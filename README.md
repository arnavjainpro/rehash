# rehash

Remembers **why** project ideas were rejected — so a new pitch that fails
for the same underlying reason gets flagged before the team re-debates a
dead end.

It matches on **rejection reasoning**, not idea wording. A support-policy
agent and an incident-runbook agent can look unrelated and still share one
fatal flaw.

A human always decides. rehash warns; it never auto-rejects.

**Fair call / Not the same thing** writes to `match_feedback`. Those
corrections are read back into the next verdict — the archive learns.

---

## Quick start (UI, offline)

No MongoDB or API keys needed:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

USE_MOCK=1 python3 app.py
```

Open **http://127.0.0.1:5050**

- Click **Should match** → Check archive  
- Click **Should look new** → Check archive  
- Open **Archive** to browse stored rejections  

```bash
USE_MOCK=1 python3 pressure_test.py
python3 demo_script.py             # stage directions (voice = skip by default)
```

---

## Live setup

```bash
cp .env.example .env   # fill keys — see table
pip install -r requirements.txt
python3 app.py         # http://127.0.0.1:5050  (no USE_MOCK)
```

| Variable | Required? | Role |
|---|---|---|
| `MONGODB_URI` | live | Atlas `rejected_ideas` + `match_feedback` |
| `OPENROUTER_API_KEY` | live | Embeddings + quality LLM (extract, verdict) |
| `FIREWORKS_API_KEY` | optional | Fast speculation path; falls back to OpenRouter |
| `ELEVENLABS_API_KEY` | optional | Mic STT + two-voice reveal |
| `LANGCHAIN_TRACING_V2` + `LANGCHAIN_API_KEY` | optional | LangSmith traces for the full check pipeline |

Seed only if the collection is empty (**`seed.py` wipes first**):

```bash
python3 seed.py && python3 create_index.py && python3 verify.py
```

Voice (only after a human has heard it on this machine):

```bash
python3 demo.py "An agent that compares what support reps actually do against the official policy doc and flags the gaps."
```

---

## How it works

```
pitch
  → Fireworks (fast) speculates likely flaw     # OpenRouter fallback
  → embed flaw (OpenRouter / text-embedding-3-small)
  → MongoDB Atlas Vector Search (top 3)         # recall
  → load prior "Not the same thing" feedback
  → OpenRouter verdict gate                     # precision
  → UI (+ optional ElevenLabs two-voice reveal)
```

There is **no similarity threshold**. Measured true/false matches overlap on
raw Atlas scores; the LLM gate decides, using human feedback as caution.

LangSmith: every live step is `@traceable` (`speculate` → `embed` →
`vector search` → `feedback cautions` → `verdict` → `check_new_idea`).

---

## Partner integrations (what each one does)

| Tool | Where | Why it’s load-bearing |
|---|---|---|
| **MongoDB Atlas Vector Search** | `match.find_closest_past_rejection` | Top-3 candidates *are* what the gate judges; no search → no verdict |
| **OpenRouter** | `config.embed`, `complete_json` | Embeddings + quality path (extract, verdict) |
| **Fireworks** | `config.complete_json_fast` | Live speculation while the audience waits; falls back if unset |
| **LangSmith** | `config.traceable` wrappers | Nested trace of the multi-step check; no-ops if unset |
| **ElevenLabs** | `voice.py`, `/api/transcribe` | Scribe STT in; streaming two-voice TTS out |

---

## UI

| Screen | Purpose |
|---|---|
| **Pitch** | One text box + mic. Demo chips for reliability. |
| **File** | Add a rejected idea + why it died → extract → embed → Mongo. |
| **Verdict** | Reaction → archive quote → **shared flaw** (`verdict_why`). **Fair call** / **Not the same thing** → `match_feedback`. |
| **Archive** | Searchable stored rejections. |

Scores are never shown as percentages (Atlas uses `(1+cos)/2`).

---

## Project map

| File | Role |
|---|---|
| `app.py` + `static/` | Web UI |
| `config.py` | Mongo, OpenRouter, Fireworks, LangSmith helpers |
| `match.py` | Speculate → search → feedback-aware verdict |
| `extract.py` / `seed.py` | Store rejections (seed wipes) |
| `voice.py` / `demo.py` | Spoken pitch + two-voice reveal |
| `pressure_test.py` | Offline + optional `--live` tests |
| `demo_script.py` | Stage directions |

---

## Best demo pitches

**Should match:**

> An agent that compares what support reps actually do against the official policy doc and flags the gaps.

**Should look new:**

> A tool that generates personalized workout playlists based on a runner’s pace and heart-rate zones, pulled from a licensed catalog.
