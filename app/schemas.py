from pydantic import BaseModel, EmailStr, Field
from datetime import date
from decimal import Decimal
class OTPRequest(BaseModel):
    mobile: str = Field(pattern=r"^[0-9]{10}$")

class OTPVerifyRequest(BaseModel):
    mobile: str = Field(pattern=r"^[0-9]{10}$")
    otp: str = Field(pattern=r"^[0-9]{6}$")

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: int

class InvoiceCreateRequest(BaseModel):
    conversation_id: int
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    payment_status: str = Field(pattern=r"^(paid|unpaid|pending)$")

class ConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=200)
    
class InvoiceConfirmRequest(BaseModel):
    confirmation_id: str = Field(min_length=1, max_length=36)
    confirmed: bool

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    mobile: str = Field(pattern=r"^[0-9]{10,15}$")
    email: EmailStr


class RegisterResponse(BaseModel):
    message: str
    customer_id: int
