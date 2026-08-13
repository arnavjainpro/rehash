# rehash

Remembers *why* project ideas were rejected, so a new idea with the same
underlying flaw gets flagged before the team re-debates a dead end.

The key design decision: we embed the **rejection reasoning**, not the idea text.
"An AI negotiation agent" and "a household chore-nagging agent" share no surface
wording, but both die of "thin on real-world impact, reads as a novelty demo" —
matching on the reasoning catches that; matching on the idea text never would.

A human always makes the final call. This flags patterns; it never auto-rejects.

## This repo: Person A — extraction pipeline

Ingestion only (extract → embed → store). Person B builds the matching/query half
against the same `hackathon.rejected_ideas` collection.

| File | What it does |
|---|---|
| `config.py` | MongoDB + OpenAI clients, `embed()`, `complete_json()`, shared constants |
| `extract.py` | `add_rejected_idea(idea_text, discussion_text)` — the pipeline |
| `seed.py` | Populates 5 real rejected ideas (wipes collection first, safe to re-run) |
| `create_index.py` | One-time Atlas Vector Search index creation |
| `verify.py` | Prints stored documents to confirm embeddings landed |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install pymongo openai python-dotenv

cp .env.example .env   # then fill in MONGODB_URI and OPENAI_API_KEY
```

`.env` is gitignored — never commit real credentials.

## Run, in order

```bash
.venv/bin/python seed.py          # 1. extract + embed + insert 5 documents
.venv/bin/python create_index.py  # 2. create reason_vector_index (needs docs to exist first)
.venv/bin/python verify.py        # 3. confirm 5 docs with 1536-dim embeddings
```

Atlas builds the index asynchronously — give it ~1 minute before querying.

## Schema (shared contract with Person B — do not rename)

Database `hackathon`, collection `rejected_ideas`:

```
{
  idea_summary:     string,
  core_mechanic:    string,
  rejection_reason: string,
  reason_embedding: float[1536],   # text-embedding-3-small, cosine
  created_at:       datetime
}
```

Vector search index: `reason_vector_index` on `reason_embedding`, cosine, 1536 dims.
