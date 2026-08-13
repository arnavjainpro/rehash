"""Flask UI + thin API around check_new_idea().

    .venv/bin/pip install -r requirements.txt
    .venv/bin/python app.py
    open http://127.0.0.1:5050

    USE_MOCK=1 .venv/bin/python app.py   # no Atlas / OpenRouter needed
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

USE_MOCK = os.environ.get("USE_MOCK") == "1"

app = Flask(__name__, static_folder="static", static_url_path="/static")

REVIEWER_PERSONA = """You are the in-house skeptic on a product team — the one \
who has sat through every brainstorm for years and remembers all of them. Dry, \
world-weary, unimpressed but not cruel. You've heard a thousand pitches and \
most of them twice.

You will be told whether a new idea matches a previously rejected one. Write \
ONE short spoken line — at most 14 words — reacting in the moment, before the \
archive reads the old reason aloud. Speak it, don't narrate it. No stage \
directions, no quotes, no preamble.

Return JSON: {"line": "<your line>"}"""

MOCK_ARCHIVE = [
    {
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
        "created_at": "2026-08-13T00:00:00+00:00",
    },
    {
        "_id": "mock-2",
        "idea_summary": (
            "An agent that diffs a team's official runbook against what "
            "actually worked in live incident chat, and flags the gap."
        ),
        "core_mechanic": (
            "compares prescribed procedure to observed practice and surfaces divergence"
        ),
        "rejection_reason": (
            "if the agent can reliably detect the runbook is wrong, the fix is "
            "to update the runbook — a permanent parallel system to flag a "
            "fixable problem doesn't make sense"
        ),
        "created_at": "2026-08-13T00:00:00+00:00",
    },
]


def _jsonable(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if k != "reason_embedding"}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _reviewer_line(result: dict) -> str:
    if USE_MOCK:
        if result.get("match"):
            return "Heard this one before. Archive has the receipt."
        return "Nothing on file. Might actually be new."

    from config import complete_json

    if result.get("match"):
        situation = (
            f"The new idea is: {result['new_idea']}\n"
            f"It matches a past rejected idea: {result['match']['idea_summary']}\n"
            "React like you recognize it. The archive is about to read the old "
            "reason aloud, so hand off to it."
        )
    else:
        situation = (
            f"The new idea is: {result['new_idea']}\n"
            "Nothing in the archive matches it. React with mild, guarded "
            "surprise. Keep it to at most 8 words."
        )
    try:
        return json.loads(complete_json(REVIEWER_PERSONA, situation))["line"].strip()
    except Exception:
        return (
            "I've seen this one before."
            if result.get("match")
            else "Nothing matches. Might be new."
        )


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/check")
def api_check():
    data = request.get_json(silent=True) or {}
    pitch = (data.get("pitch") or "").strip()
    if not pitch:
        return jsonify({"error": "pitch is required"}), 400
    if len(pitch) < 8:
        return jsonify({"error": "pitch is too short to judge — add a sentence"}), 400

    from match import check_new_idea

    try:
        result = check_new_idea(pitch)
    except Exception as exc:
        return jsonify({"error": f"check failed: {exc}"}), 500

    payload = _jsonable(result)
    payload["reviewer_line"] = _reviewer_line(result)
    # Never surface raw retrieval scores in the UI contract as percentages.
    if payload.get("match"):
        payload["match"].pop("score", None)
    for c in payload.get("candidates") or []:
        c.pop("score", None)
    if payload.get("raw_top_match"):
        payload["raw_top_match"].pop("score", None)
    return jsonify(payload)


@app.post("/api/feedback")
def api_feedback():
    data = request.get_json(silent=True) or {}
    if "was_real_match" not in data:
        return jsonify({"error": "was_real_match is required"}), 400

    result = {
        "new_idea": data.get("new_idea", ""),
        "speculated_flaw": data.get("speculated_flaw", ""),
        "match": data.get("match"),
        "raw_top_match": data.get("raw_top_match") or data.get("match"),
    }
    from match import log_human_feedback

    doc = log_human_feedback(result, bool(data["was_real_match"]))
    return jsonify(_jsonable(doc))


@app.post("/api/reject")
def api_reject():
    """File a rejected idea into the archive (Person A write path)."""
    data = request.get_json(silent=True) or {}
    idea = (data.get("idea") or data.get("idea_text") or "").strip()
    discussion = (data.get("discussion") or data.get("discussion_text") or "").strip()
    if not idea:
        return jsonify({"error": "idea is required"}), 400
    if not discussion:
        return jsonify({"error": "discussion (why it was rejected) is required"}), 400
    if len(idea) < 8 or len(discussion) < 8:
        return jsonify({"error": "idea and discussion need a bit more detail"}), 400

    if USE_MOCK:
        doc = {
            "_id": f"mock-{len(MOCK_ARCHIVE) + 1}",
            "idea_summary": idea.split("\n")[0][:160],
            "core_mechanic": (
                "mock mechanic extracted from the idea without domain nouns"
            ),
            "rejection_reason": discussion.split("\n")[0][:400],
            "created_at": datetime.now().astimezone().isoformat(),
        }
        MOCK_ARCHIVE.insert(0, doc)
        return jsonify(_jsonable(doc))

    from extract import add_rejected_idea

    try:
        doc = add_rejected_idea(idea, discussion)
    except Exception as exc:
        return jsonify({"error": f"extract/store failed: {exc}"}), 500
    return jsonify(_jsonable(doc))


@app.get("/api/archive")
def api_archive():
    q = (request.args.get("q") or "").strip().lower()

    if USE_MOCK:
        docs = MOCK_ARCHIVE
    else:
        from config import collection

        docs = list(
            collection.find(
                {},
                {
                    "idea_summary": 1,
                    "core_mechanic": 1,
                    "rejection_reason": 1,
                    "created_at": 1,
                },
            ).sort("created_at", -1)
        )

    docs = _jsonable(docs)
    if q:
        docs = [
            d
            for d in docs
            if q in (d.get("idea_summary") or "").lower()
            or q in (d.get("rejection_reason") or "").lower()
            or q in (d.get("core_mechanic") or "").lower()
        ]
    return jsonify({"items": docs, "count": len(docs)})


@app.post("/api/transcribe")
def api_transcribe():
    """Optional mic path: browser uploads audio, ElevenLabs Scribe returns text."""
    if "audio" not in request.files:
        return jsonify({"error": "audio file required"}), 400
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return jsonify({"error": "ELEVENLABS_API_KEY not set"}), 503

    audio = request.files["audio"]
    suffix = os.path.splitext(audio.filename or "clip.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = tmp.name
        audio.save(path)

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
        with open(path, "rb") as f:
            result = client.speech_to_text.convert(file=f, model_id="scribe_v1")
        text = (result.text or "").strip()
    except Exception as exc:
        return jsonify({"error": f"transcription failed: {exc}"}), 502
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    return jsonify({"text": text})


if __name__ == "__main__":
    # Match module reads USE_MOCK at import; keep process env consistent.
    if USE_MOCK:
        print("Running with USE_MOCK=1 (no live MongoDB / OpenRouter calls)")
    else:
        print("Running LIVE (MongoDB + OpenRouter from .env)")
    port = int(os.environ.get("PORT", "5050"))
    # use_reloader=False avoids double-import quirks with USE_MOCK / clients.
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
