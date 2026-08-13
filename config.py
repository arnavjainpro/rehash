"""Shared clients and helpers for the rehash extraction pipeline."""

import os

from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

load_dotenv()

DB_NAME = "hackathon"
COLLECTION_NAME = "rejected_ideas"
VECTOR_INDEX_NAME = "reason_vector_index"

# Routed through OpenRouter, so models carry the "openai/" prefix. Both are the
# real OpenAI models; text-embedding-3-small is 1536 dims either way.
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHAT_MODEL = "openai/gpt-4o-mini"

mongo_client = MongoClient(os.environ["MONGODB_URI"])
collection = mongo_client[DB_NAME][COLLECTION_NAME]

openai_client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)


def embed(text: str) -> list[float]:
    """Embed a single string with text-embedding-3-small (1536 dims)."""
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def complete_json(system_prompt: str, user_prompt: str) -> str:
    """Call the chat model and return its raw JSON response string."""
    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
