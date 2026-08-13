"""One-time creation of the Atlas Vector Search index on reason_embedding.

Run this AFTER seed.py — Atlas needs at least one document containing the
embedding field before the index builds cleanly.
"""

from pymongo.operations import SearchIndexModel

from config import EMBEDDING_DIMENSIONS, VECTOR_INDEX_NAME, collection

INDEX = SearchIndexModel(
    name=VECTOR_INDEX_NAME,
    type="vectorSearch",
    definition={
        "fields": [
            {
                "type": "vector",
                "path": "reason_embedding",
                "numDimensions": EMBEDDING_DIMENSIONS,
                "similarity": "cosine",
            }
        ]
    },
)


def main():
    existing = [i["name"] for i in collection.list_search_indexes()]
    if VECTOR_INDEX_NAME in existing:
        print(f"Index '{VECTOR_INDEX_NAME}' already exists — nothing to do.")
        return

    if collection.count_documents({"reason_embedding": {"$exists": True}}) == 0:
        raise SystemExit("No documents with reason_embedding yet. Run seed.py first.")

    collection.create_search_index(INDEX)
    print(f"Created '{VECTOR_INDEX_NAME}'. Atlas builds it asynchronously (~1 min).")


if __name__ == "__main__":
    main()
