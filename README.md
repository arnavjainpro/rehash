# rehash

Remembers *why* project ideas were rejected, so a new idea with the same
underlying flaw gets flagged before the team re-debates a dead end.

The key design decision: we embed the **rejection reasoning**, not the idea text.
"An AI negotiation agent" and "a household chore-nagging agent" share no surface
wording, but both die of "thin on real-world impact, reads as a novelty demo" —
matching on the reasoning catches that; matching on the idea text never would.

A human always makes the final call. This flags patterns; it never auto-rejects.

## Files

| File | Owner | What it does |
|---|---|---|
| `config.py` | shared | MongoDB + OpenRouter clients, `embed()`, `complete_json()`, constants |
| `extract.py` | A | `add_rejected_idea(idea_text, discussion_text)` — extract → embed → store |
| `seed.py` | A | Populates 5 real rejected ideas (wipes collection first, safe to re-run) |
| `create_index.py` | A | One-time Atlas Vector Search index creation |
| `verify.py` | A | Prints stored documents to confirm embeddings landed |
| `match.py` | B | `check_new_idea(idea_text)` — speculate flaw → embed → vector search |
| `TEST_CASES.md` | B | Ready-to-run pitches for live threshold tuning |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install pymongo openai python-dotenv requests

cp .env.example .env   # fill in MONGODB_URI and OPENROUTER_API_KEY
```

Everything routes through OpenRouter (`openai/text-embedding-3-small`,
`openai/gpt-4o-mini`). `.env` is gitignored — never commit real credentials.

Optional: `ELEVENLABS_API_KEY` enables voice narration of match verdicts in
`match.py` (no-ops cleanly if unset).

## Run Person A (seed), in order

```bash
.venv/bin/python seed.py          # 1. extract + embed + insert 5 documents
.venv/bin/python create_index.py  # 2. create reason_vector_index (needs docs first)
.venv/bin/python verify.py        # 3. confirm 5 docs with 1536-dim embeddings
```

Atlas builds the index asynchronously — give it ~1 minute before querying.
(Index is already created on the shared cluster.)

## Run Person B (match)

```bash
# offline rehearsal (no creds / no seed needed):
USE_MOCK=1 .venv/bin/python match.py

# live, against seeded Atlas data:
.venv/bin/python match.py
```

Or from a REPL / demo script:

```python
from match import check_new_idea, display_match
display_match(check_new_idea("your pitch here"))
```

See `TEST_CASES.md` for nine pitches: same-flaw matches, no-match, and a
false-positive stress test (similar wording, different flaw).

**Threshold:** seeded reasons sit ~0.29–0.59 cosine apart. Default
`SIMILARITY_THRESHOLD = 0.60` — above that only fires on close matches;
below ~0.45 starts flagging unrelated ideas. Tune against live scores
(`raw_top_match` is always returned).

## Schema (do not rename)

Database `hackathon`, collection `rejected_ideas`:

```
{
  idea_summary:     string,
  core_mechanic:    string,
  rejection_reason: string,          # this is what gets embedded
  reason_embedding: float[1536],     # text-embedding-3-small, cosine
  created_at:       datetime
}
```

Vector search index: `reason_vector_index` on `reason_embedding`, cosine, 1536 dims.

Query side must embed the *speculated failure mode*, not the raw pitch —
vectors live in reasoning-space, not idea-space.

## Voice layer (ElevenLabs)

Speak a pitch; hear the archive answer in two distinct voices.

```bash
.venv/bin/python demo.py                          # speak the pitch
.venv/bin/python demo.py "typed pitch here"       # skip the mic
USE_MOCK=1 .venv/bin/python demo.py "pitch"       # no Atlas needed
```

| File | What it does |
|---|---|
| `voice.py` | Scribe STT in, streaming TTS out, two-voice reveal |
| `demo.py` | End-to-end: pitch -> match -> spoken verdict |

**How it works.** `record_until_silence()` captures the pitch and ElevenLabs
Scribe transcribes it, feeding `check_new_idea()` unchanged. On a match, a
"reviewer" voice (Roger) reacts live — the line is written per-run by an LLM
held to a dry, world-weary persona — then an "archive" voice (Matilda, flat
settings) reads the stored `rejection_reason` back verbatim, so the system's
memory audibly speaks in a voice of its own.

TTS uses the **streaming** endpoint with `pcm_24000` output piped straight to
the output device, so playback starts before generation completes (first audio
typically 400-800ms). Raw PCM also means no `ffmpeg`/decoder dependency.

Requires `ELEVENLABS_API_KEY` in `.env`. Recording needs microphone permission
for your terminal.
