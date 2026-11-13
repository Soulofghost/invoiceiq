import os
import pytest
from fastapi.testclient import TestClient

os.environ["SQLITE_DB_PATH"] = ":memory:"

from app.main import app
from app.database import init_db

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

client = TestClient(app)

def test_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_analytics_summary():
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_invoices"] >= 2
    assert data["total_spend"] > 0
    assert data["reconciliation_rate"] >= 0.0

def test_extract_endpoint():
    res = client.post("/api/v1/invoices/extract", json={
        "raw_text": "Invoice #INV-TEST-44\nDate: 2026-11-09\nFrom: Cloudflare Inc\nSubtotal: $200.00\nTax: $20.00\nTotal: $220.00"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["invoice_number"] == "INV-TEST-44"
    assert data["vendor_name"] == "Cloudflare Inc"
    assert data["is_reconciled"] is True

def test_invoice_crud_and_status_transition():
    # 1. Create invoice
    create_res = client.post("/api/v1/invoices", json={
        "invoice_number": "INV-API-881",
        "vendor_name": "MongoDB Atlas",
        "vendor_tax_id": "US-2819401",
        "invoice_date": "2026-11-02",
        "due_date": "2026-12-02",
        "currency": "USD",
        "subtotal": 1000.0,
        "tax_amount": 80.0,
        "total_amount": 1080.0,
        "line_items": [
            {"description": "M30 Cluster Dedicated RAM", "quantity": 1, "unit_price": 1000.0, "total": 1000.0}
        ]
    })
    assert create_res.status_code == 201
    inv = create_res.json()
    inv_id = inv["id"]
    assert inv["status"] == "PENDING_REVIEW"
    assert inv["is_reconciled"] is True

    # 2. Get invoice by ID
    get_res = client.get(f"/api/v1/invoices/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["invoice_number"] == "INV-API-881"

    # 3. Transition status to APPROVED
    patch_res = client.patch(f"/api/v1/invoices/{inv_id}/status", json={
        "status": "APPROVED"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "APPROVED"
