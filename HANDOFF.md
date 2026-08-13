# rehash — status handoff

**Repo:** https://github.com/arnavjainpro/rehash

**What it does:** Stores *why* past ideas were rejected, not just that they
were. A new pitch gets its likely flaw speculated (Fireworks fast path),
that reasoning is embedded and vector-searched against stored rejection
reasons, prior human false-positive feedback is loaded, and an OpenRouter
verdict gate decides whether the new idea repeats an old mistake.

## Architecture

| File | Role |
|---|---|
| `config.py` | Mongo + OpenRouter + Fireworks + LangSmith `traceable` |
| `extract.py` | `add_rejected_idea()` — quality-path extract → embed → store |
| `seed.py` | 5 real rejected ideas (**wipes collection first**) |
| `create_index.py` | One-time vector index creation |
| `match.py` | `check_new_idea()` — speculate → search → feedback → verdict |
| `voice.py` / `demo.py` | Scribe STT + two-voice reveal |
| `app.py` + `static/` | Pitch / verdict / archive UI |

`hackathon.rejected_ideas` + `hackathon.match_feedback`. Index
`reason_vector_index` on `reason_embedding` (1536-dim, cosine).

## Frontend integration

Call `check_new_idea(pitch)`. Returns `match`, `verdict_why`, `candidates`,
`feedback_cautions_used`, speculated fields. `log_human_feedback()` writes
corrections that later calls read back via `load_feedback_cautions()`.

## Gotchas

1. **No similarity threshold** — true/false scores overlap in embedding
   space. The LLM gate is the precision step. Don't re-add a threshold.
2. **Atlas returns `(1 + cosine) / 2`**, not raw cosine. Don't show as %.
3. **`seed.py` wipes the collection.** Don't run casually on shared data.
4. **Voice is skip-by-default** in `demo_script.py` until a human has
   heard the full two-voice reveal on the demo machine.
5. **Fireworks / LangSmith are optional at runtime** but wired in code:
   unset keys → OpenRouter / no-op tracing. Set keys for the full path.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
USE_MOCK=1 .venv/bin/python pressure_test.py
.venv/bin/python app.py          # live
USE_MOCK=1 .venv/bin/python app.py
```
