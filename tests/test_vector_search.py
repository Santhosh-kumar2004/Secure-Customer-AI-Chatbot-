
from app.vector_store import search_customer_invoices


def test_customer_invoice_isolation():
    # Search invoices for Customer 1
    customer_1_results = search_customer_invoices(
        question="Show my unpaid invoices",
        customer_id=1,
        top_k=5,
        payment_status="unpaid",
    )

    # Search invoices for Customer 2
    customer_2_results = search_customer_invoices(
        question="Show my unpaid invoices",
        customer_id=2,
        top_k=5,
        payment_status="unpaid",
    )

    # Extract metadata
    customer_1_metadata = customer_1_results.get("metadatas", [[]])[0]
    customer_2_metadata = customer_2_results.get("metadatas", [[]])[0]

    # Customer 1 must only receive Customer 1 invoices
    for metadata in customer_1_metadata:
        assert metadata["customer_id"] == 1

    # Customer 2 must only receive Customer 2 invoices
    for metadata in customer_2_metadata:
        assert metadata["customer_id"] == 2

    print("Customer invoice isolation test passed!")


if __name__ == "__main__":
    test_customer_invoice_isolation()
