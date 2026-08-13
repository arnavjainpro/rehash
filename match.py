"""Person B — matching / query half.

Takes a NEW idea pitch, speculates its likely failure mode, embeds that
reasoning, and vector-searches it against stored rejection_reason embeddings.

Critical: we embed the *speculated flaw*, not the raw pitch text. The vectors
in Mongo live in reasoning-space (Person A's rejection_reason embeddings), so
embedding idea text would never hit anything meaningful.

Can run offline with USE_MOCK=1 before credentials / seed data are ready.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

USE_MOCK = os.environ.get("USE_MOCK") == "1"

# config.py connects at import time — only pull it in for live runs.
if not USE_MOCK:
    from config import (  # noqa: E402
        DB_NAME,
        VECTOR_INDEX_NAME,
        collection,
        complete_json,
        embed,
        mongo_client,
    )

FEEDBACK_COLLECTION_NAME = "match_feedback"

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

MOCK_SPECULATION = {
    "core_mechanic": (
        "retrieves relevant text at query time and stuffs it into a prompt"
    ),
    "likely_flaw": (
        "retrieval only fills the prompt, it doesn't change what the "
        "system does next -- no persistent state, no adaptation, no "
        "action taken on real data"
    ),
}

MOCK_MATCH = {
    "_id": "mock-1",
    "idea_summary": (
        "A support chatbot that answers questions about internal docs by "
        "embedding them and retrieving relevant chunks at query time."
    ),
    "core_mechanic": (
        "retrieves relevant text at query time and stuffs it into a prompt"
    ),
    "rejection_reason": (
        "retrieval only fills the prompt, it doesn't change what the "
        "system does next -- no persistent state, no adaptation, no "
        "action taken on real data"
    ),
    "score": 0.91,
}

SPECULATE_SYSTEM_PROMPT = """You are pressure-testing a new project idea \
before it gets built. You will be given a new idea. You don't know yet \
whether it's good or bad.

Return JSON with exactly two string fields:
- "core_mechanic": what the idea actually DOES, stripped of domain-specific \
wording, same style as: "logs an outcome, then recommends an action to a \
human based on matching it to similar past outcomes"
- "likely_flaw": the most likely underlying flaw this idea could have — \
concrete and generalizable, not "it might not work". Something like: \
"the value only exists in a narrow band between what's already tracked \
elsewhere and what's too minor to matter". This text will be embedded and \
compared against past rejection reasons, so write it as a failure mechanism \
that could be recognized in a completely different domain.
"""

# No similarity threshold: measured true and false matches overlap (a false
# pitch scored 0.714 against true matches at 0.696-0.706), because all abstract
# failure-mode prose sits in a narrow band. verdict_gate() decides instead.


def speculate_on_new_idea(idea_text: str) -> dict:
    """LLM guesses the new idea's mechanic + likely flaw, before any lookup."""
    if USE_MOCK:
        return dict(MOCK_SPECULATION)
    raw = complete_json(SPECULATE_SYSTEM_PROMPT, idea_text)
    parsed = json.loads(raw)
    if "core_mechanic" not in parsed or "likely_flaw" not in parsed:
        raise ValueError(f"Expected core_mechanic + likely_flaw, got: {raw!r}")
    return {
        "core_mechanic": parsed["core_mechanic"].strip(),
        "likely_flaw": parsed["likely_flaw"].strip(),
    }


def find_closest_past_rejection(likely_flaw: str, top_k: int = 1) -> list[dict]:
    """Embed the speculated flaw and Atlas Vector Search stored reasons."""
    if USE_MOCK:
        return [dict(MOCK_MATCH)][:top_k]

    query_vector = embed(likely_flaw)

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "reason_embedding",
                "queryVector": query_vector,
                "numCandidates": 50,
                "limit": top_k,
            }
        },
        {
            "$project": {
                "idea_summary": 1,
                "core_mechanic": 1,
                "rejection_reason": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(collection.aggregate(pipeline))


VERDICT_SYSTEM_PROMPT = """You are the gate that decides whether a new project idea repeats a past mistake.

Vector search over past rejection reasons is a recall step only — it always returns its nearest candidates, even when nothing genuinely matches. Your job is precision: decide whether the new idea would actually fail for the SAME underlying reason as one of the candidates.

Be strict. Reject a candidate if:
- the resemblance is topical (both involve agents, both involve data) rather than a shared failure mechanism
- the new idea shares the candidate's subject matter but not its flaw
- you are merely picking the least-bad option — "none" is the right answer far more often than not

Accept only when you could explain to the person who pitched it: "this fails for the same reason that one did, and here is the mechanism."

Return JSON:
{"match_index": <0-based index of the matching candidate, or -1 for none>,
 "why": "<one sentence: the shared failure mechanism, or why none matched>"}"""


def verdict_gate(idea_text: str, speculated_flaw: str, candidates: list[dict]) -> dict:
    """Precision gate over the vector-search candidates.

    Embedding similarity alone cannot separate real matches here — all
    abstract failure-mode prose sits in a narrow similarity band — so an LLM
    makes the final call over the top candidates.
    """
    if USE_MOCK:
        return {"match_index": 0, "why": "mock verdict"}

    listing = "\n".join(
        f"[{i}] idea: {c['idea_summary']}\n    rejected because: {c['rejection_reason']}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        f"NEW IDEA: {idea_text}\n"
        f"ITS LIKELY FLAW (speculated): {speculated_flaw}\n\n"
        f"PAST REJECTED IDEAS:\n{listing}"
    )
    parsed = json.loads(complete_json(VERDICT_SYSTEM_PROMPT, prompt))
    return {"match_index": int(parsed.get("match_index", -1)),
            "why": str(parsed.get("why", "")).strip()}


def check_new_idea(idea_text: str) -> dict:
    """Speculate -> embed flaw -> vector search (recall) -> LLM gate (precision)."""
    speculation = speculate_on_new_idea(idea_text)
    candidates = find_closest_past_rejection(speculation["likely_flaw"], top_k=3)

    verdict = verdict_gate(idea_text, speculation["likely_flaw"], candidates)
    idx = verdict["match_index"]
    matched = candidates[idx] if 0 <= idx < len(candidates) else None

    return {
        "new_idea": idea_text,
        "speculated_mechanic": speculation["core_mechanic"],
        "speculated_flaw": speculation["likely_flaw"],
        "match": matched,
        "verdict_why": verdict["why"],
        "raw_top_match": candidates[0] if candidates else None,
        "candidates": candidates,
    }


def log_human_feedback(result: dict, was_real_match: bool):
    """Log whether a human confirmed the match. Separate collection only."""
    match = result.get("match") or result.get("raw_top_match")
    doc = {
        "new_idea": result["new_idea"],
        "speculated_flaw": result["speculated_flaw"],
        "matched_idea_id": match["_id"] if match else None,
        "match_score": match["score"] if match else None,
        "was_real_match": was_real_match,
        "created_at": datetime.now(timezone.utc),
    }
    if USE_MOCK:
        print(f"[mock] would log feedback: {doc}")
        return doc
    mongo_client[DB_NAME][FEEDBACK_COLLECTION_NAME].insert_one(doc)
    return doc


def _verdict_line(result: dict) -> str:
    if result["match"]:
        m = result["match"]
        return (
            f"Ah. I've seen this one before. Filed under: {m['idea_summary']} "
            f"It died because {m['rejection_reason']} "
            f"Same bones, different skin."
        )
    return "Huh. Doesn't match anything in the archive. This one might actually be new."


def narrate_verdict(result: dict, out_path: str = "verdict.mp3") -> Optional[str]:
    """ElevenLabs TTS of the verdict. No-ops if ELEVENLABS_API_KEY is unset."""
    if not ELEVENLABS_API_KEY:
        return None

    import requests

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": _verdict_line(result),
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
        },
        timeout=30,
    )
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def display_match(result: dict):
    print("=" * 70)
    print(f"NEW IDEA: {result['new_idea']}")
    print(f"  mechanic (guessed): {result['speculated_mechanic']}")
    print(f"  likely flaw (guessed): {result['speculated_flaw']}")
    print("-" * 70)

    if result["match"]:
        m = result["match"]
        print(f"⚠️  MATCH FOUND (retrieval score: {m['score']:.3f})")
        print(f"  Looks like: {m['idea_summary']}")
        print(f"  Which was rejected because: {m['rejection_reason']}")
        print(f"  Shared flaw: {result['verdict_why']}")
    else:
        top = result["raw_top_match"]
        if top:
            print("No match — this one looks genuinely new.")
            print(f"  {result['verdict_why']}")
            print(f"  (nearest was {top['score']:.3f}: {top['idea_summary'][:50]})")
        else:
            print("No past rejections in the database yet.")
    print("=" * 70)


if __name__ == "__main__":
    # USE_MOCK=1 python3 match.py  -> fully offline
    # python3 match.py             -> live Atlas + OpenRouter
    if USE_MOCK:
        print("(running in USE_MOCK mode -- no live MongoDB/OpenRouter calls)\n")

    test_idea = (
        "A compliance agent that watches how support reps actually resolve "
        "billing disputes in chat and flags where that diverges from the "
        "official policy doc."
    )
    result = check_new_idea(test_idea)
    display_match(result)
    log_human_feedback(result, was_real_match=True)

    audio_path = narrate_verdict(result)
    if audio_path:
        print(f"(voice verdict saved to {audio_path})")
    else:
        print("(ELEVENLABS_API_KEY not set -- skipping voice narration)")
