
from unittest.mock import patch

from app.database import SessionLocal
from app.models import Invoice
from app.vector_store import index_invoice


db = SessionLocal()

try:
    # Choose an existing invoice without changing its database record
    invoice = db.query(Invoice).first()

    if invoice is None:
        print("FAIL: No invoice found in PostgreSQL.")
    else:
        print("Invoice found:", invoice.invoice_number)
        print("Invoice ID:", invoice.id)

        # Simulate ChromaDB indexing failure
        try:
            with patch(
                "app.vector_store.collection.upsert",
                side_effect=RuntimeError("Simulated indexing failure"),
            ):
                index_invoice(invoice, invoice.customer_id)
        except RuntimeError as exc:
            print("Expected indexing failure:", exc)

        # Confirm the invoice still exists in PostgreSQL
        db.expire_all()
        saved_invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice.id)
            .first()
        )

        if saved_invoice:
            print("PASS: Invoice remains in PostgreSQL.")
        else:
            print("FAIL: Invoice not found in PostgreSQL.")

        # Retry indexing normally
        index_invoice(saved_invoice, saved_invoice.customer_id)
        print("Recovery indexing call completed.")

finally:
    db.close()
