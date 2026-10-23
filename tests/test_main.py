from fastapi.testclient import TestClient
from app.models import Customer
from app.main import app,get_current_customer
client = TestClient(app)

def test_app_is_running():
    response = client.get("/")

    assert response.status_code == 200

def test_register_endpoint_exists():
    response = client.post("/register", json={})

    assert response.status_code in [400, 422]

def test_protected_endpoint_requires_login():
    response = client.get("/auth/me")

    assert response.status_code in [401, 403, 404, 405]

def test_customer_cannot_access_another_customers_conversation():
    response = client.post(
        "/chat",
        json={
            "conversation_id": 999999,
            "question": "Show my invoice details"
        },
    )

    assert response.status_code in [401, 403, 404]

def test_request_otp_requires_mobile():
    response = client.post("/auth/request-otp", json={})

    assert response.status_code in [400, 422]


def test_verify_otp_requires_otp():
    response = client.post(
        "/auth/verify-otp",
        json={"mobile": "9000000001"}
    )

    assert response.status_code in [400, 401, 422]

def test_create_conversation_requires_login():
    response = client.post("/conversations")

    assert response.status_code in [401, 403]


def test_list_conversations_requires_login():
    response = client.get("/conversations")

    assert response.status_code in [401, 403]

def test_list_invoices_requires_login():
    response = client.get("/invoices")

    assert response.status_code in [401, 403]


def test_invoice_preview_requires_login():
    response = client.post("/invoices/preview", json={})

    assert response.status_code in [401, 403]

def test_invoice_confirmation_requires_login():
    response = client.post(
        "/invoices/confirm",
        json={}
    )

    assert response.status_code in [401, 403]

def test_invoice_preview_rejects_invalid_amount():
    response = client.post(
        "/invoices/preview",
        json={
            "conversation_id": 1,
            "invoice_number": "TEST-INVALID-AMOUNT",
            "invoice_date": "2026-10-22",
            "amount": -100,
            "currency": "INR",
            "payment_status": "unpaid"
        }
    )

    assert response.status_code == 401


def test_invoice_preview_rejects_invalid_payment_status():
    response = client.post(
        "/invoices/preview",
        json={
            "conversation_id": 1,
            "invoice_number": "TEST-INVALID-STATUS",
            "invoice_date": "2026-10-22",
            "amount": 1000,
            "currency": "INR",
            "payment_status": "unknown"
        }
    )

    assert response.status_code == 401
def test_invoice_preview_rejects_invalid_amount_when_authenticated():
    test_customer = Customer(
        id=1,
        name="Test Customer",
        mobile="9000000001",
        email="test@example.com",
    )

    app.dependency_overrides[get_current_customer] = lambda: test_customer

    try:
        response = client.post(
            "/invoices/preview",
            json={
                "conversation_id": 999999,
                "invoice_number": "TEST-INVALID-AMOUNT",
                "invoice_date": "2026-10-22",
                "amount": -100,
                "currency": "INR",
                "payment_status": "unpaid",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

def test_invoice_preview_rejects_invalid_payment_status_when_authenticated():
    test_customer = Customer(
        id=1,
        name="Test Customer",
        mobile="9000000001",
        email="test@example.com",
    )

    app.dependency_overrides[get_current_customer] = lambda: test_customer

    try:
        response = client.post(
            "/invoices/preview",
            json={
                "conversation_id": 999999,
                "invoice_number": "TEST-INVALID-STATUS",
                "invoice_date": "2026-10-22",
                "amount": 1000,
                "currency": "INR",
                "payment_status": "unknown",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

def test_invoice_confirmation_requires_existing_pending_confirmation():
    test_customer = Customer(
        id=1,
        name="Test Customer",
        mobile="9000000001",
        email="test@example.com",
    )

    app.dependency_overrides[get_current_customer] = lambda: test_customer

    try:
        response = client.post(
            "/invoices/confirm",
            json={
                "confirmation_id": "invalid-confirmation-id",
                "confirmed": True,
            },
        )

        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_customer, None)