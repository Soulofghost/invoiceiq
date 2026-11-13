import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db_connection
from app.schemas import (
    InvoiceExtractRequest, InvoiceCreateRequest, InvoiceResponse,
    InvoiceStatusUpdateRequest, InvoiceAnalyticsSummary
)
from app.engine.extractor import extract_invoice_data

router = APIRouter(prefix="", tags=["Invoices & Extraction"])

@router.post("/invoices/extract")
def extract_from_text(req: InvoiceExtractRequest):
    data = extract_invoice_data(req.raw_text)
    return data

@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(req: InvoiceCreateRequest):
    inv_id = "INV-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Verify arithmetic reconciliation
    line_sum = sum(item.total for item in req.line_items)
    is_reconciled = (abs(line_sum - req.subtotal) <= 0.05) and (abs((req.subtotal + req.tax_amount) - req.total_amount) <= 0.05)
    anomalies = []
    if not is_reconciled:
        anomalies.append("ARITHMETIC_MISMATCH: Declared totals do not reconcile with line item sums.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (
                id, invoice_number, vendor_name, vendor_tax_id, invoice_date, due_date,
                currency, subtotal, tax_amount, total_amount, status, is_reconciled,
                has_anomalies, anomalies_json, line_items_json, raw_text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id, req.invoice_number.strip(), req.vendor_name.strip(), req.vendor_tax_id,
            req.invoice_date.strip(), req.due_date, req.currency.upper(), req.subtotal,
            req.tax_amount, req.total_amount, "PENDING_REVIEW", 1 if is_reconciled else 0,
            1 if anomalies else 0, json.dumps(anomalies),
            json.dumps([item.model_dump() for item in req.line_items]), req.raw_text or "",
            now_iso, now_iso
        ))
        conn.commit()

        cursor.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,))
        r = cursor.fetchone()
        return InvoiceResponse(
            id=r["id"],
            invoice_number=r["invoice_number"],
            vendor_name=r["vendor_name"],
            vendor_tax_id=r["vendor_tax_id"],
            invoice_date=r["invoice_date"],
            due_date=r["due_date"],
            currency=r["currency"],
            subtotal=r["subtotal"],
            tax_amount=r["tax_amount"],
            total_amount=r["total_amount"],
            status=r["status"],
            is_reconciled=bool(r["is_reconciled"]),
            has_anomalies=bool(r["has_anomalies"]),
            anomalies=json.loads(r["anomalies_json"]),
            line_items=json.loads(r["line_items_json"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

@router.get("/invoices", response_model=List[InvoiceResponse])
def get_invoices(status: Optional[str] = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM invoices"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status.upper())
        query += " ORDER BY created_at DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [
            InvoiceResponse(
                id=r["id"],
                invoice_number=r["invoice_number"],
                vendor_name=r["vendor_name"],
                vendor_tax_id=r["vendor_tax_id"],
                invoice_date=r["invoice_date"],
                due_date=r["due_date"],
                currency=r["currency"],
                subtotal=r["subtotal"],
                tax_amount=r["tax_amount"],
                total_amount=r["total_amount"],
                status=r["status"],
                is_reconciled=bool(r["is_reconciled"]),
                has_anomalies=bool(r["has_anomalies"]),
                anomalies=json.loads(r["anomalies_json"]) if r["anomalies_json"] else [],
                line_items=json.loads(r["line_items_json"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
            for r in rows
        ]

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceResponse(
            id=r["id"],
            invoice_number=r["invoice_number"],
            vendor_name=r["vendor_name"],
            vendor_tax_id=r["vendor_tax_id"],
            invoice_date=r["invoice_date"],
            due_date=r["due_date"],
            currency=r["currency"],
            subtotal=r["subtotal"],
            tax_amount=r["tax_amount"],
            total_amount=r["total_amount"],
            status=r["status"],
            is_reconciled=bool(r["is_reconciled"]),
            has_anomalies=bool(r["has_anomalies"]),
            anomalies=json.loads(r["anomalies_json"]) if r["anomalies_json"] else [],
            line_items=json.loads(r["line_items_json"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(invoice_id: str, req: InvoiceStatusUpdateRequest):
    valid_statuses = ["PENDING_REVIEW", "VERIFIED", "APPROVED", "PAID", "REJECTED"]
    new_status = req.status.upper()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE invoices SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_iso, invoice_id))
        conn.commit()

        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return InvoiceResponse(
            id=r["id"],
            invoice_number=r["invoice_number"],
            vendor_name=r["vendor_name"],
            vendor_tax_id=r["vendor_tax_id"],
            invoice_date=r["invoice_date"],
            due_date=r["due_date"],
            currency=r["currency"],
            subtotal=r["subtotal"],
            tax_amount=r["tax_amount"],
            total_amount=r["total_amount"],
            status=r["status"],
            is_reconciled=bool(r["is_reconciled"]),
            has_anomalies=bool(r["has_anomalies"]),
            anomalies=json.loads(r["anomalies_json"]) if r["anomalies_json"] else [],
            line_items=json.loads(r["line_items_json"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

@router.get("/analytics/summary", response_model=InvoiceAnalyticsSummary)
def get_analytics_summary():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        total_inv = cursor.execute("SELECT count(*) FROM invoices").fetchone()[0]
        spend_row = cursor.execute("SELECT SUM(total_amount) FROM invoices").fetchone()[0]
        total_spend = round(float(spend_row), 2) if spend_row is not None else 0.0

        appr_row = cursor.execute("SELECT SUM(total_amount) FROM invoices WHERE status IN ('APPROVED', 'PAID')").fetchone()[0]
        approved_spend = round(float(appr_row), 2) if appr_row is not None else 0.0

        pending = cursor.execute("SELECT count(*) FROM invoices WHERE status = 'PENDING_REVIEW'").fetchone()[0]
        anomalies = cursor.execute("SELECT count(*) FROM invoices WHERE has_anomalies = 1").fetchone()[0]
        reconciled = cursor.execute("SELECT count(*) FROM invoices WHERE is_reconciled = 1").fetchone()[0]

        reconciliation_rate = round((reconciled / total_inv) * 100, 1) if total_inv > 0 else 100.0

        return InvoiceAnalyticsSummary(
            total_invoices=total_inv,
            total_spend=total_spend,
            approved_spend=approved_spend,
            pending_approvals=pending,
            anomalies_detected=anomalies,
            reconciliation_rate=reconciliation_rate
        )
