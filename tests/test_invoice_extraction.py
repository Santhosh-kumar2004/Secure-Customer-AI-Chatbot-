from app.llm_service import extract_invoice_details

question = "Create invoice INV-2001, date 2026-10-22, amount 3000 INR, status unpaid"

details = extract_invoice_details(question)

required_fields = [
    "invoice_number",
    "invoice_date",
    "amount",
    "currency",
    "payment_status",
]

missing_fields = [
    field for field in required_fields
    if details.get(field) is None
]

print("Extracted details:", details)
print("Missing fields:", missing_fields)