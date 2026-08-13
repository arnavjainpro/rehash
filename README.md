# rehash

Remembers **why** project ideas were rejected — so a new pitch that fails
for the same underlying reason gets flagged before the team re-debates a
dead end.

It matches on **rejection reasoning**, not idea wording. A support-policy
agent and an incident-runbook agent can look unrelated and still share one
fatal flaw.

A human always decides. rehash warns; it never auto-rejects.

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

Pressure-test everything offline:

```bash
USE_MOCK=1 python3 pressure_test.py
```

Run the spoken demo walkthrough:

```bash
python3 demo_script.py             # what to say / click
USE_MOCK=1 python3 demo_script.py --run   # also execute the checks
python3 demo_script.py --ui        # how to launch the UI
```

---

## Live setup (real Atlas + models)

1. Copy env and fill keys:

```bash
cp .env.example .env
```

| Variable | Required for | Notes |
|---|---|---|
| `MONGODB_URI` | live match / seed | Atlas connection string |
| `OPENROUTER_API_KEY` | live LLM + embeddings | Routes `gpt-4o-mini` + `text-embedding-3-small` |
| `ELEVENLABS_API_KEY` | mic / voice demo | Optional; UI still works without it |

2. Install + seed (only if the shared collection is empty — **seed wipes data**):

```bash
pip install -r requirements.txt
python3 seed.py            # wipes rejected_ideas, then inserts 5 examples
python3 create_index.py    # one-time vector index (skip if already created)
python3 verify.py          # confirm docs + 1536-dim embeddings
```

3. Start the UI live:

```bash
python3 app.py
```

4. Optional terminal voice demo:

```bash
python3 demo.py "An agent that compares what support reps actually do against the official policy doc and flags the gaps."
```

Add your IP under Atlas → Network Access, or connections hang instead of failing cleanly.

---

## What you’ll see in the UI

| Screen | Purpose |
|---|---|
| **Pitch** | One text box + mic. Demo chips load known pitches. |
| **Verdict** | Reaction → quoted past rejection → **shared flaw** (largest text). Then **Fair call** / **Not the same thing**. |
| **Archive** | Searchable list of stored rejections (proof the memory is real). |

Similarity percentages are **intentionally hidden**. Atlas returns `(1 + cosine) / 2`, which looks like a broken “probability” if shown as %.

---

## How it works

```
pitch
  → LLM speculates likely flaw
  → embed that flaw
  → MongoDB Atlas Vector Search (top 3)     # recall
  → LLM verdict gate                        # precision
  → UI / voice reveal
```

There is **no similarity threshold**. True and false matches overlap on raw
scores; the LLM gate decides whether the failure mechanism is actually the same.

---

## Project map

| File | Role |
|---|---|
| `app.py` | Web UI + `/api/check`, `/api/feedback`, `/api/archive` |
| `static/` | Pitch / verdict / archive front-end |
| `match.py` | `check_new_idea()` — speculate → search → verdict |
| `extract.py` / `seed.py` | Store rejected ideas (seed **wipes** first) |
| `create_index.py` / `verify.py` | Index + sanity check |
| `voice.py` / `demo.py` | Mic STT + two-voice spoken reveal |
| `pressure_test.py` | Automated offline (and optional live) tests |
| `demo_script.py` | Stage directions for the live demo |
| `TEST_CASES.md` | Extra pitches for tuning |
| `HANDOFF.md` | Engineering gotchas |

---

## Best demo pitches

**Should match** (different domain, same flaw as the runbook rejection):

> An agent that compares what support reps actually do against the official policy doc and flags the gaps.

**Should look new**:

> A tool that generates personalized workout playlists based on a runner’s pace and heart-rate zones, pulled from a licensed catalog.

---

## API (for the UI / integrations)

```bash
curl -s http://127.0.0.1:5050/api/check \
  -H 'content-type: application/json' \
  -d '{"pitch":"your idea here"}'
```

Useful response fields: `match`, `verdict_why`, `reviewer_line`,
`speculated_flaw`, `candidates`. Feedback: `POST /api/feedback` with
`was_real_match: true|false`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI works but always “mock” answers | Start without `USE_MOCK=1` and set `.env` |
| Live check hangs | Allow your IP in Atlas Network Access |
| Empty archive live | Collection may be empty — ask before running `seed.py` (it wipes) |
| Mic fails | Needs `ELEVENLABS_API_KEY`, or use typed pitch / browser speech fallback |
| `pressure_test.py` fails after editing match | Re-run with `USE_MOCK=1` so imports pick up mock mode |
