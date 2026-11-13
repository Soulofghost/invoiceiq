from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float
    total: float

class InvoiceExtractRequest(BaseModel):
    raw_text: str = Field(..., json_schema_extra={"example": "Invoice #INV-2026-990\nDate: 2026-11-10\nFrom: Snowflake Inc\nSubtotal: $1500.00\nTax: $120.00\nTotal: $1620.00"})

class InvoiceCreateRequest(BaseModel):
    invoice_number: str
    vendor_name: str
    vendor_tax_id: Optional[str] = None
    invoice_date: str
    due_date: Optional[str] = None
    currency: str = "USD"
    subtotal: float
    tax_amount: float
    total_amount: float
    line_items: List[LineItem]
    raw_text: Optional[str] = None

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    vendor_name: str
    vendor_tax_id: Optional[str] = None
    invoice_date: str
    due_date: Optional[str] = None
    currency: str
    subtotal: float
    tax_amount: float
    total_amount: float
    status: str
    is_reconciled: bool
    has_anomalies: bool
    anomalies: List[str]
    line_items: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class InvoiceStatusUpdateRequest(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "APPROVED"})

class InvoiceAnalyticsSummary(BaseModel):
    total_invoices: int
    total_spend: float
    approved_spend: float
    pending_approvals: int
    anomalies_detected: int
    reconciliation_rate: float
