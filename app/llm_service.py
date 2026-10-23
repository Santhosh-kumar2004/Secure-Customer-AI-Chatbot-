
import os
import json
from dotenv import load_dotenv
from ollama import Client

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")


def get_client():
    if not OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY is missing in .env")

    return Client(
        host="https://ollama.com",
        headers={
            "Authorization": f"Bearer {OLLAMA_API_KEY}"
        }
    )



def understand_request(
    question: str,
    invoices: list,
    conversation_history: list = None
) -> dict:
    """Understand customer request using invoices and chat history."""

    if conversation_history is None:
        conversation_history = []

    prompt = f"""
You are a secure customer support assistant.

Customer invoices:
{json.dumps(invoices, default=str)}

Previous conversation messages:
{json.dumps(conversation_history, default=str)}

Current customer question:
{question}

Rules:
1. Use only the provided customer invoices and conversation history.
2. Never reveal another customer's information.
3. If asked about invoices, answer using the provided invoice records.
4. Use previous messages to answer questions about details
   the customer shared earlier, such as their name.
5. If the information is not available, clearly say you
   could not find it in the available records or conversation.
6. If the customer wants to create an invoice, do not create it.
7. For invoice creation, return action "create_invoice".
8. Required invoice fields:
   invoice_number, invoice_date, amount, currency, payment_status.
9. Do not invent missing invoice details.
10. For normal questions, return action "answer".
11. Return valid JSON only, using this format:

{{
  "action": "answer",
  "answer": "Your answer here",
  "missing_fields": []
}}
"""

    client = get_client()

    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format="json"
    )

    try:
        result = json.loads(response.message.content)
    except (json.JSONDecodeError, TypeError):
        return {
            "action": "answer",
            "answer": "Sorry, I could not process your request. Please try again.",
            "missing_fields": []
        }

    if result.get("action") not in ["answer", "create_invoice"]:
        return {
            "action": "answer",
            "answer": "Sorry, I could not process your request.",
            "missing_fields": []
        }

    return result

def extract_invoice_details(question: str) -> dict:
    """Extract invoice fields from the customer's message."""

    prompt = f"""
Extract invoice details from the customer message.

Customer message:
{question}

Return valid JSON only with these fields:
{{
  "invoice_number": null,
  "invoice_date": null,
  "amount": null,
  "currency": null,
  "payment_status": null
}}

Rules:
- Do not invent missing values.
- invoice_date must use YYYY-MM-DD format.
- amount must be a positive number.
- currency must be a three-letter code, such as INR.
- payment_status must be paid, unpaid, or pending.
- If a value is missing, return null.
"""

    client = get_client()

    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        format="json",
    )

    import json

    try:
        result = json.loads(response.message.content)
    except (json.JSONDecodeError, TypeError):
        return {}

    required_fields = [
        "invoice_number",
        "invoice_date",
        "amount",
        "currency",
        "payment_status",
    ]

    return {
        field: result.get(field)
        for field in required_fields
    }

