
from app.llm_service import understand_request

invoices = [
    {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-10-01",
        "amount": "2500.00",
        "currency": "INR",
        "payment_status": "unpaid"
    }
]

question = "Show my unpaid invoices"

result = understand_request(question, invoices)

print(result)
