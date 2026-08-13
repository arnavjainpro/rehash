# rehash — status handoff

**Repo:** https://github.com/arnavjainpro/rehash

**What it does:** Stores *why* past ideas were rejected, not just that they
were. A new pitch gets its likely flaw speculated by an LLM, that reasoning is
embedded and vector-searched against stored rejection reasons, and a gate
decides whether the new idea repeats an old mistake. Cross-domain by design — a
support-policy pitch correctly matches an incident-runbook rejection.

## Architecture

| File | Role |
|---|---|
| `config.py` | Mongo + OpenRouter clients, `embed()`, `complete_json()` |
| `extract.py` | `add_rejected_idea()` — extract → embed reasoning → store |
| `seed.py` | 5 real rejected ideas (**wipes collection first**) |
| `create_index.py` | One-time vector index creation |
| `match.py` | `check_new_idea()` — speculate → search → verdict gate |
| `voice.py` | Scribe STT in, streaming TTS out, two-voice reveal |
| `demo.py` | End-to-end entry point |

`hackathon.rejected_ideas`, index `reason_vector_index` on `reason_embedding`
(1536-dim, cosine). Fields: `idea_summary`, `core_mechanic`,
`rejection_reason`, `reason_embedding`, `created_at`. **Don't rename any of
these.**

## Frontend integration point

Call `check_new_idea(pitch)`. It returns:

- `match` — the matched document, or `None`
- `verdict_why` — one sentence on the shared flaw (worth surfacing in the UI,
  it's the payoff)
- `candidates` — top 3 from vector search
- `speculated_mechanic`, `speculated_flaw`, `raw_top_match`

For voice, `two_voice_reveal(result)` plays the whole reveal.

## Four things that will otherwise cost you an hour

1. **There is no similarity threshold, deliberately.** Measured true and false
   matches overlap on every numeric signal — a kids' multiplication-drills
   pitch scored 0.714 against genuine matches at 0.696–0.706, and gap/z-score
   separated no better. All abstract failure-mode prose sits in a narrow
   embedding band. `verdict_gate()` (an LLM call over the top 3) makes the call
   instead. **Don't re-add a threshold.**
2. **Atlas returns `(1 + cosine) / 2`, not raw cosine.** Confirmed
   empirically. Any score from `$vectorSearch` is on that scale.
3. **Everything routes through OpenRouter**, not OpenAI directly — models are
   `openai/text-embedding-3-small` and `openai/gpt-4o-mini` (note the prefix).
   A direct OpenAI key works too; same model, same dims.
4. **`seed.py` wipes the collection.** The data got emptied once already.
   Don't run it casually against shared data.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # MONGODB_URI, OPENROUTER_API_KEY, ELEVENLABS_API_KEY
.venv/bin/python demo.py "your pitch here"
USE_MOCK=1 .venv/bin/python demo.py "pitch"   # works with no Atlas/creds
```

Add your IP under Atlas → Network Access, or connections silently time out
(TCP connects, then the handshake is dropped — it looks like a hang, not an
auth error). ElevenLabs runs on the free tier: 10,000 characters.

## Best demo pitch

> "An agent that compares what support reps actually do against the official
> policy doc and flags the gaps."

Matches the incident-runbook rejection. Different domain, same flaw — the thing
text search can't do.

## Open

- Voice output has never been heard by a human — needs an ear check that the
  reviewer and archive voices are audibly distinct.
- Voice layer 3 (confidence-driven modulation) unstarted.
- One known false negative: the LLM-router pitch. The speculator guesses a
  mechanical flaw while the stored reason is about market crowding, so the gate
  correctly says they don't match.
