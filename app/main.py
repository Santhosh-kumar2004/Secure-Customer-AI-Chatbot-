from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.security import create_access_token,decode_access_token
from app.database import SessionLocal,get_db
from app.auth_service import create_otp, verify_otp
from app.schemas import (RegisterRequest,RegisterResponse,OTPRequest,OTPVerifyRequest,
ChatRequest,InvoiceConfirmRequest,InvoiceCreateRequest,ConversationRequest)
from sqlalchemy.exc import IntegrityError
from app.models import Customer,Invoice,Conversation,Message,PendingInvoice
from app.llm_service import (understand_request,extract_invoice_details)
from app.vector_store import search_customer_invoices,index_invoice 
from app.memory_service import (
    save_memory,
    get_memory_value,
    extract_name,
)

app = FastAPI(title="Secure Customer AI Chatbot")

from uuid import uuid4

bearer_scheme = HTTPBearer()

def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        customer_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=401, detail="Customer not found")

    return customer
@app.get("/")
def home():
    return {"message": "Customer AI Chatbot API is running"}

@app.post("/register", response_model=RegisterResponse)
def register_customer(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    customer = Customer(
        name=data.name.strip(),
        mobile=data.mobile.strip(),
        email=str(data.email).strip().lower(),
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Phone number or email already registered",
        )

    return {
        "message": "Registration successful. You can now log in using your phone number.",
        "customer_id": customer.id,
    }

@app.post("/auth/request-otp")
def request_otp(data: OTPRequest, db: Session = Depends(get_db)):
    success, message = create_otp(db, data.mobile)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # OTP is not included in the API response.
    return {"message": message}


@app.post("/auth/verify-otp")
def verify_otp_endpoint(
    data: OTPVerifyRequest,
    db: Session = Depends(get_db),
):
    success, result = verify_otp(db, data.mobile, data.otp)

    if not success:
        raise HTTPException(status_code=401, detail=result)

    access_token = create_access_token(result.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }

@app.get("/auth/me")
def get_me(customer: Customer = Depends(get_current_customer)):
    return {
        "id": customer.id,
        "name": customer.name,
        "mobile": customer.mobile,
    }

@app.get("/invoices")
def get_my_invoices(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer.id)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )

    return {
        "customer_id": customer.id,
        "total": len(invoices),
        "invoices": [
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date.isoformat(),
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "payment_status": invoice.payment_status,
            }
            for invoice in invoices
        ],
    }


@app.post("/chat")
def chat_with_customer(
    data: ChatRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == data.conversation_id,
            Conversation.customer_id == customer.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # Save the user's message
    user_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        role="user",
        content=data.question,
    )
    db.add(user_message)
    db.commit()

    try:
        question = data.question.strip()
        question_lower = question.lower()

        # 1. Save name when the customer shares it
        saved_name = extract_name(question)

        if saved_name:
            save_memory(
                db=db,
                customer_id=customer.id,
                memory_key="name",
                memory_value=saved_name,
            )

            answer = (
                f"Nice to meet you, {saved_name}! "
                "I will remember your name."
            )

        # 2. Retrieve the saved name when asked
        elif any(
            phrase in question_lower
            for phrase in [
                "what is my name",
                "what's my name",
                "do you remember my name",
                "tell me my name",
            ]
        ):
            saved_name = get_memory_value(
                db=db,
                customer_id=customer.id,
                memory_key="name",
            )

            if saved_name:
                answer = f"Your name is {saved_name}."
            else:
                answer = (
                    "I don't have your name saved yet. "
                    "Tell me: My name is Arun."
                )

        else:
            # 3. Get this customer's invoice records
            invoices = (
                db.query(Invoice)
                .filter(Invoice.customer_id == customer.id)
                .order_by(Invoice.invoice_date.desc())
                .all()
            )

            invoice_records = [
                {
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat(),
                    "amount": str(inv.amount),
                    "currency": inv.currency,
                    "payment_status": inv.payment_status,
                }
                for inv in invoices
            ]

            # 4. Load recent conversation history
            previous_messages = (
                db.query(Message)
                .filter(
                    Message.conversation_id == conversation.id,
                    Message.customer_id == customer.id,
                    Message.id != user_message.id,
                )
                .order_by(
                    Message.created_at.desc(),
                    Message.id.desc(),
                )
                .limit(10)
                .all()
            )
            previous_messages.reverse()

            conversation_history = [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in previous_messages
            ]

            # 5. Search only this customer's invoice vectors
            payment_status = None

            if "unpaid" in question_lower:
                payment_status = "unpaid"
            elif "pending" in question_lower:
                payment_status = "pending"
            elif "paid" in question_lower:
                payment_status = "paid"

            vector_results = search_customer_invoices(
                question=question,
                customer_id=customer.id,
                top_k=5,
                payment_status=payment_status,
            )

            documents = vector_results.get(
                "documents", [[]]
            )[0]

            # 6. Ask the existing LLM to understand the request
            intent = understand_request(
                question=question,
                invoices=documents,
                conversation_history=conversation_history,
            )

            if intent.get("action") == "create_invoice":
                details = extract_invoice_details(question)

                required_fields = [
                    "invoice_number",
                    "invoice_date",
                    "amount",
                    "currency",
                    "payment_status",
                ]

                missing_fields = [
                    field
                    for field in required_fields
                    if details.get(field) is None
                    or details.get(field) == ""
                ]

                if missing_fields:
                    answer = (
                        "Please provide these invoice details: "
                        + ", ".join(missing_fields)
                    )
                else:
                    try:
                        invoice_data = InvoiceCreateRequest(
                            conversation_id=conversation.id,
                            **details,
                        )
                    except Exception:
                        answer = (
                            "Some invoice details are invalid. "
                            "Please check the date, amount, "
                            "currency and payment status."
                        )
                    else:
                        existing = (
                            db.query(Invoice)
                            .filter(
                                Invoice.customer_id == customer.id,
                                Invoice.invoice_number
                                == invoice_data.invoice_number,
                            )
                            .first()
                        )

                        if existing:
                            answer = (
                                "This invoice number already exists."
                            )
                        else:
                            confirmation_id = str(uuid4())

                            pending_invoice = PendingInvoice(
                                confirmation_id=confirmation_id,
                                customer_id=customer.id,
                                conversation_id=conversation.id,
                                invoice_number=invoice_data.invoice_number,
                                invoice_date=invoice_data.invoice_date,
                                amount=invoice_data.amount,
                                currency=invoice_data.currency,
                                payment_status=invoice_data.payment_status,
                                status="pending",
                            )

                            db.add(pending_invoice)
                            db.commit()

                            answer = (
                                "Invoice preview created. "
                                f"Invoice number: "
                                f"{pending_invoice.invoice_number}. "
                                f"Amount: {pending_invoice.amount} "
                                f"{pending_invoice.currency}. "
                                f"Confirmation ID: {confirmation_id}. "
                                "Please confirm before saving the invoice."
                            )

            else:
                answer = intent.get(
                    "answer",
                    "I could not find this information in your records.",
                )

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=502,
            detail="Unable to process your request with the AI service.",
        )

    # Save the assistant's response
    assistant_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        role="assistant",
        content=answer,
    )
    db.add(assistant_message)
    db.commit()

    return {
        "conversation_id": conversation.id,
        "question": data.question,
        "answer": answer,
    }

@app.post("/conversations")
def create_conversation(
    data: ConversationRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    conversation = Conversation(
        customer_id=customer.id,
        title=data.title,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "conversation_id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
    }

@app.get("/conversations")
def get_conversations(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.customer_id == customer.id)
        .order_by(desc(Conversation.created_at))
        .all()
    )

    return [
        {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
        }
        for conversation in conversations
    ]

@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.customer_id == customer.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.customer_id == customer.id,
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    return {
        "conversation_id": conversation.id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }

@app.post("/invoices/preview")
def preview_invoice(
    data: InvoiceCreateRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    # Verify conversation ownership
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == data.conversation_id,
            Conversation.customer_id == customer.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check duplicate invoice number for this customer
    existing = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer.id,
            Invoice.invoice_number == data.invoice_number,
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=409, detail="Invoice number already exists")

    # Save pending confirmation in PostgreSQL
    confirmation_id = str(uuid4())

    pending = PendingInvoice(
        confirmation_id=confirmation_id,
        customer_id=customer.id,
        conversation_id=conversation.id,
        invoice_number=data.invoice_number,
        invoice_date=data.invoice_date,
        amount=data.amount,
        currency=data.currency,
        payment_status=data.payment_status,
        status="pending",
    )

    db.add(pending)
    db.commit()

    return {
        "confirmation_id": confirmation_id,
        "message": "Review this invoice and confirm before creation.",
        "invoice_preview": {
            "invoice_number": data.invoice_number,
            "invoice_date": data.invoice_date.isoformat(),
            "amount": str(data.amount),
            "currency": data.currency,
            "payment_status": data.payment_status,
        },
    }
@app.post("/invoices/confirm")
def confirm_invoice(
    data: InvoiceConfirmRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    # Only the owner can access this confirmation
    pending = (
        db.query(PendingInvoice)
        .filter(
            PendingInvoice.confirmation_id == data.confirmation_id,
            PendingInvoice.customer_id == customer.id,
            PendingInvoice.status == "pending",
        )
        .with_for_update()
        .first()
    )

    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Pending confirmation not found or already processed",
        )

    if not data.confirmed:
        pending.status = "cancelled"
        db.commit()
        return {"message": "Invoice creation cancelled"}

    # Check duplicate again before creation
    existing = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer.id,
            Invoice.invoice_number == pending.invoice_number,
        )
        .first()
    )

    if existing:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Invoice number already exists",
        )

    invoice = Invoice(
        customer_id=customer.id,
        invoice_number=pending.invoice_number,
        invoice_date=pending.invoice_date,
        amount=pending.amount,
        currency=pending.currency,
        payment_status=pending.payment_status,
    )

    try:
        db.add(invoice)
        pending.status = "confirmed"

        db.commit()
        db.refresh(invoice)

    except Exception as e:
        db.rollback()
        print(f"Invoice creation failed: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to create invoice",
        )

    # Index separately after invoice is saved
    try:
        index_invoice(
            invoice=invoice,
            customer_id=customer.id
        )
        print(f"Invoice {invoice.id} indexed successfully")

    except Exception as e:
        print(f"Invoice indexing failed: {e}")

    return {
        "message": "Invoice created successfully",
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "amount": str(invoice.amount),
        "currency": invoice.currency,
    }
