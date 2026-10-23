
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Customer, OTPVerification


OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()

def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def create_otp(db: Session, mobile: str):
    customer = (
        db.query(Customer)
        .filter(Customer.mobile == mobile)
        .first()
    )

    if not customer:
        return None, "Customer not found"

    now = datetime.now(timezone.utc)
    latest_otp = (
        db.query(OTPVerification)
        .filter(OTPVerification.customer_id == customer.id)
        .order_by(OTPVerification.created_at.desc())
        .first()
    )

    if latest_otp:
        elapsed = (now - latest_otp.created_at).total_seconds()

        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            return None, "Please wait before requesting another OTP"

    otp = generate_otp()

    record = OTPVerification(
        customer_id=customer.id,
        otp_hash=hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        attempts=0,
        created_at=now,
        is_used=False,
    )

    db.add(record)
    db.commit()

    print(f"DEV OTP for {mobile}: {otp}")

    return True, "OTP generated"

def verify_otp(db: Session, mobile: str, entered_otp: str):
    customer = (
        db.query(Customer)
        .filter(Customer.mobile == mobile)
        .first()
    )

    if not customer:
        return False, "Customer not found"

    record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.customer_id == customer.id,
            OTPVerification.is_used == False,
        )
        .order_by(OTPVerification.created_at.desc())
        .first()
    )

    if not record:
        return False, "No active OTP found"

    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now >= expires_at:
        record.is_used = True
        db.commit()
        return False, "OTP expired"

    if record.attempts >= OTP_MAX_ATTEMPTS:
        record.is_used = True
        db.commit()
        return False, "Maximum OTP attempts exceeded"

    record.attempts += 1

    if not secrets.compare_digest(
        record.otp_hash,
        hash_otp(entered_otp),
    ):
        if record.attempts >= OTP_MAX_ATTEMPTS:
            record.is_used = True

        db.commit()
        return False, "Invalid OTP"

    record.is_used = True
    db.commit()

    return True, customer
