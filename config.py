"""Shared clients and helpers for the rehash extraction pipeline.

Two LLM paths (both fail open to OpenRouter if the preferred key is missing):
- complete_json()      — quality path via OpenRouter (extraction, verdict gate)
- complete_json_fast() — latency path via Fireworks (live speculation)

LangSmith: wrap call sites with @traceable. Set LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY (or LANGSMITH_API_KEY) to see nested traces; no-ops otherwise.
"""

from __future__ import annotations

import os
from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

load_dotenv()

DB_NAME = "hackathon"
COLLECTION_NAME = "rejected_ideas"
FEEDBACK_COLLECTION_NAME = "match_feedback"
VECTOR_INDEX_NAME = "reason_vector_index"

# Routed through OpenRouter, so models carry the "openai/" prefix.
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHAT_MODEL = "openai/gpt-4o-mini"

# Fireworks open-weight fast path for live speculation during the demo.
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY")
FIREWORKS_MODEL = os.environ.get(
    "FIREWORKS_MODEL",
    "accounts/fireworks/models/llama-v3p3-70b-instruct",
)

mongo_client = MongoClient(os.environ["MONGODB_URI"])
collection = mongo_client[DB_NAME][COLLECTION_NAME]

openai_client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

_fireworks_client = (
    OpenAI(
        api_key=FIREWORKS_API_KEY,
        base_url="https://api.fireworks.ai/inference/v1",
    )
    if FIREWORKS_API_KEY
    else None
)


def _noop_traceable(func: Callable = None, **_kwargs):  # type: ignore[assignment]
    """Drop-in stand-in when langsmith isn't installed or configured."""
    if func is not None and callable(func):
        return func

    def decorator(fn: Callable) -> Callable:
        return fn

    return decorator


try:
    from langsmith import traceable as _ls_traceable

    traceable = _ls_traceable
except Exception:  # pragma: no cover - optional dependency
    traceable = _noop_traceable  # type: ignore[assignment]


@traceable(name="embed_text")
def embed(text: str) -> list[float]:
    """Embed a single string with text-embedding-3-small (1536 dims)."""
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


@traceable(name="llm_call_quality_openrouter")
def complete_json(system_prompt: str, user_prompt: str) -> str:
    """Quality-path chat call via OpenRouter. Returns raw JSON response text."""
    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


@traceable(name="llm_call_fast_fireworks")
def complete_json_fast(system_prompt: str, user_prompt: str) -> str:
    """Latency-sensitive chat call via Fireworks; falls back to OpenRouter.

    Used for Person B's live speculation — the call the audience waits on.
    """
    if _fireworks_client is None:
        return complete_json(system_prompt, user_prompt)

    # Prefer JSON mode when the model supports it; fall back to plain + parse.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = _fireworks_client.chat.completions.create(
            model=FIREWORKS_MODEL,
            response_format={"type": "json_object"},
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception:
        response = _fireworks_client.chat.completions.create(
            model=FIREWORKS_MODEL,
            messages=messages,
        )
        return response.choices[0].message.content
