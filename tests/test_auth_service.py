from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from app.auth_service import (
    create_otp,
    verify_otp,
    hash_otp,
    OTP_MAX_ATTEMPTS,
)

def test_hash_otp_is_consistent():
    assert hash_otp("123456") == hash_otp("123456")
    assert hash_otp("123456") != hash_otp("654321")

def test_unknown_customer_cannot_request_otp():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    success, message = create_otp(db, "9999999999")
    assert success is None
    assert message == "Customer not found"

def test_unknown_customer_cannot_verify_otp():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    success, message = verify_otp(db, "9999999999", "123456")
    assert success is False
    assert message == "Customer not found"

def test_expired_otp_is_rejected():
    db = MagicMock()
    customer = MagicMock(id=1)
    record = MagicMock()
    record.customer_id = 1
    record.is_used = False
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    record.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    record.attempts = 0
    record.otp_hash = hash_otp("123456")

    customer_query = db.query.return_value
    customer_query.filter.return_value.first.return_value = customer

    otp_query = MagicMock()
    otp_query.filter.return_value.order_by.return_value.first.return_value = record
    db.query.side_effect = [customer_query, otp_query]

    success, message = verify_otp(db, "9000000001", "123456")

    assert success is False
    assert message == "OTP expired"
    assert record.is_used is True
    db.commit.assert_called_once()

def test_wrong_otp_is_rejected():
    db = MagicMock()
    customer = MagicMock(id=1)
    record = MagicMock()
    record.customer_id = 1
    record.is_used = False
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    record.created_at = datetime.now(timezone.utc)
    record.attempts = 0
    record.otp_hash = hash_otp("123456")

    customer_query = db.query.return_value
    customer_query.filter.return_value.first.return_value = customer

    otp_query = MagicMock()
    otp_query.filter.return_value.order_by.return_value.first.return_value = record
    db.query.side_effect = [customer_query, otp_query]

    success, message = verify_otp(db, "9000000001", "000000")

    assert success is False
    assert message == "Invalid OTP"
    assert record.attempts == 1
    db.commit.assert_called_once()

def test_maximum_otp_attempts_constant():
    assert OTP_MAX_ATTEMPTS == 5

def test_fifth_wrong_otp_attempt_blocks_otp():
    db = MagicMock()
    customer = MagicMock(id=1)

    record = MagicMock()
    record.customer_id = 1
    record.is_used = False
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    record.created_at = datetime.now(timezone.utc)
    record.attempts = 4
    record.otp_hash = hash_otp("123456")

    customer_query = db.query.return_value
    customer_query.filter.return_value.first.return_value = customer

    otp_query = MagicMock()
    otp_query.filter.return_value.order_by.return_value.first.return_value = record
    db.query.side_effect = [customer_query, otp_query]

    success, message = verify_otp(db, "9000000001", "000000")

    assert success is False
    assert message == "Invalid OTP"
    assert record.attempts == 5
    assert record.is_used is True
    db.commit.assert_called_once()
    

def test_otp_resend_cooldown_blocks_new_request():
    db = MagicMock()
    customer = MagicMock(id=1)

    latest_otp = MagicMock()
    latest_otp.created_at = (
        datetime.now(timezone.utc) - timedelta(seconds=30)
    )

    customer_query = MagicMock()
    customer_query.filter.return_value.first.return_value = customer

    otp_query = MagicMock()
    otp_query.filter.return_value.order_by.return_value.first.return_value = latest_otp

    db.query.side_effect = [customer_query, otp_query]

    success, message = create_otp(db, "9000000001")

    assert success is None
    assert message == "Please wait before requesting another OTP"
    db.add.assert_not_called()
    db.commit.assert_not_called()

def test_otp_is_marked_used_after_successful_verification():
    db = MagicMock()
    customer = MagicMock(id=1)

    record = MagicMock()
    record.customer_id = 1
    record.is_used = False
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    record.created_at = datetime.now(timezone.utc)
    record.attempts = 0
    record.otp_hash = hash_otp("123456")

    customer_query = MagicMock()
    customer_query.filter.return_value.first.return_value = customer

    otp_query = MagicMock()
    otp_query.filter.return_value.order_by.return_value.first.return_value = record

    db.query.side_effect = [customer_query, otp_query]

    success, result = verify_otp(db, "9000000001", "123456")

    assert success is True
    assert result == customer
    assert record.is_used is True
    db.commit.assert_called_once()
