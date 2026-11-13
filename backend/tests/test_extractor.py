from app.engine.extractor import extract_invoice_data, parse_currency, clean_num

SAMPLE_INVOICE_TEXT = """
INVOICE #INV-2026-8891
Date: 2026-11-08
Due Date: 2026-12-08
From: Datadog Monitoring Inc
Tax ID: US-9928174

Items:
APM Enterprise Host Agent   5 x $180.00 = $900.00
Log Management Ingestion   1 x $350.00 = $350.00

Subtotal: $1,250.00
Tax: $100.00
Total Due: $1,350.00
"""

def test_extract_invoice_data_nominal():
    data = extract_invoice_data(SAMPLE_INVOICE_TEXT)
    assert data["invoice_number"] == "INV-2026-8891"
    assert data["vendor_name"] == "Datadog Monitoring Inc"
    assert data["subtotal"] == 1250.0
    assert data["tax_amount"] == 100.0
    assert data["total_amount"] == 1350.0
    assert data["currency"] == "USD"
    assert data["is_reconciled"] is True
    assert data["has_anomalies"] is False
    assert len(data["line_items"]) == 2

def test_extract_invoice_data_arithmetic_mismatch():
    bad_invoice = """
    Invoice: INV-BAD-01
    Date: 2026-11-01
    From: Dodgy Supplies LLC
    Subtotal: $1000.00
    Tax: $100.00
    Total: $2500.00
    """
    data = extract_invoice_data(bad_invoice)
    assert data["is_reconciled"] is False
    assert data["has_anomalies"] is True
    assert any("ARITHMETIC_RECONCILIATION_FAILED" in a for a in data["anomalies"])

def test_extract_abnormal_tax_rate():
    high_tax_invoice = """
    Invoice: INV-TAX-99
    Date: 2026-11-01
    From: Overcharging Corp
    Subtotal: $100.00
    Tax: $50.00
    Total: $150.00
    """
    data = extract_invoice_data(high_tax_invoice)
    assert data["has_anomalies"] is True
    assert any("ABNORMAL_TAX_RATE" in a for a in data["anomalies"])

def test_currency_parser():
    assert parse_currency("Total: 500.00 EUR") == "EUR"
    assert parse_currency("Total: £450.00") == "GBP"
    assert parse_currency("Total: $1,200.00") == "USD"

def test_clean_num():
    assert clean_num("$1,450.50") == 1450.50
    assert clean_num("€89.99") == 89.99
    assert clean_num("invalid") == 0.0
