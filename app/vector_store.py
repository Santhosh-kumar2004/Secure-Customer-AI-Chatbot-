import os
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

# Persistent vector database
client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

# Embedding model
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# Collection for customer records
collection = client.get_or_create_collection(
    name="customer_records",
    metadata={"hnsw:space": "cosine"}
)


def create_embedding(text: str) -> list[float]:
    """Convert text into a vector."""
    vector = embedding_model.encode(text)
    return vector.tolist()


def get_collection():
    """Return the ChromaDB collection."""
    return collection

def index_invoice(invoice, customer_id: int):
    """Store an invoice in ChromaDB."""

    invoice_text = (
        f"Invoice Number: {invoice.invoice_number}\n"
        f"Invoice Date: {invoice.invoice_date}\n"
        f"Amount: {invoice.amount} {invoice.currency}\n"
        f"Payment Status: {invoice.payment_status}"
    )

    collection.upsert(
        ids=[f"invoice_{invoice.id}"],
        documents=[invoice_text],
        metadatas=[{
            "customer_id": customer_id,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "record_type": "invoice",
            "payment_status": invoice.payment_status.lower()
        }],
        embeddings=[create_embedding(invoice_text)]
    )

def search_customer_invoices(
    question: str,
    customer_id: int,
    top_k: int = 5,
    payment_status: str | None = None
):
    """Search invoices belonging to one customer."""

    if top_k < 1:
        raise ValueError("top_k must be positive")

    conditions = [
        {"customer_id": customer_id},
        {"record_type": "invoice"}
    ]

    if payment_status:
        status = payment_status.lower()

        if status not in {"paid", "unpaid", "pending"}:
            raise ValueError("Invalid payment status")

        conditions.append({"payment_status": status})

    results = collection.query(
        query_embeddings=[create_embedding(question)],
        n_results=top_k,
        where={"$and": conditions}
    )

    return results
