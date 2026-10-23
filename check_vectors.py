from app.vector_store import get_collection

collection = get_collection()

data = collection.get(
    where={
        "$and": [
            {"customer_id": 1},
            {"record_type": "invoice"}
        ]
    },
    include=["documents", "metadatas"]
)

print("Customer 1 invoice vectors:", len(data["ids"]))

for vector_id, metadata, document in zip(
    data["ids"],
    data["metadatas"],
    data["documents"]
):
    print("\nID:", vector_id)
    print("Metadata:", metadata)
    print("Document:", document)