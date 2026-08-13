"""Sanity check: print what's actually stored in MongoDB."""

from config import collection

for doc in collection.find():
    print(f"\n{doc['idea_summary']}")
    print(f"  core_mechanic:    {doc['core_mechanic']}")
    print(f"  rejection_reason: {doc['rejection_reason']}")
    print(f"  reason_embedding: {len(doc['reason_embedding'])} floats, "
          f"first 3 = {[round(v, 4) for v in doc['reason_embedding'][:3]]}")
    print(f"  created_at:       {doc['created_at']}")

print(f"\nTotal: {collection.count_documents({})} documents")
print("Search indexes:", [i["name"] for i in collection.list_search_indexes()])
