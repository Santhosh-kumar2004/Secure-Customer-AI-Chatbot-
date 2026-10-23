from app.database import SessionLocal
from app.models import Invoice
from app.vector_store import index_invoice


def index_all_invoices():
    db = SessionLocal()

    try:
        invoices = db.query(Invoice).all()

        if not invoices:
            print("No invoices found in PostgreSQL.")
            return

        for invoice in invoices:
            index_invoice(
                invoice=invoice,
                customer_id=invoice.customer_id
            )

        print(f"Successfully indexed {len(invoices)} invoices.")

    except Exception as e:
        print("Indexing failed:", str(e))
        raise

    finally:
        db.close()


if __name__ == "__main__":
    index_all_invoices()
