import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from app.config import SQLITE_DB_PATH

_memory_conn = None

def get_db_connection() -> sqlite3.Connection:
    global _memory_conn
    if SQLITE_DB_PATH == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect("file:invoiceiq_mem?mode=memory&cache=shared", uri=True, check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn

    db_path = Path(SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                invoice_number TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                vendor_tax_id TEXT,
                invoice_date TEXT NOT NULL,
                due_date TEXT,
                currency TEXT NOT NULL DEFAULT 'USD',
                subtotal REAL NOT NULL,
                tax_amount REAL NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
                is_reconciled INTEGER NOT NULL DEFAULT 1,
                has_anomalies INTEGER NOT NULL DEFAULT 0,
                anomalies_json TEXT,
                line_items_json TEXT NOT NULL,
                raw_text TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_created ON invoices (created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices (invoice_number);")

        # Seed sample invoices if empty
        cnt = cursor.execute("SELECT count(*) FROM invoices").fetchone()[0]
        if cnt == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            sample_lines_1 = [
                {"description": "Cloud Infrastructure Compute (AWS EC2)", "quantity": 10, "unit_price": 120.0, "total": 1200.0},
                {"description": "Kubernetes Cluster Management", "quantity": 1, "unit_price": 500.0, "total": 500.0},
                {"description": "Managed Database Storage (RDS Postgres)", "quantity": 2, "unit_price": 150.0, "total": 300.0}
            ]
            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, vendor_name, vendor_tax_id, invoice_date, due_date,
                    currency, subtotal, tax_amount, total_amount, status, is_reconciled,
                    has_anomalies, anomalies_json, line_items_json, raw_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "INV-2026-001",
                "INV-AWS-9042",
                "Amazon Web Services EMEA SARL",
                "LU26372811",
                "2026-11-01",
                "2026-11-30",
                "USD",
                2000.0,
                160.0,
                2160.0,
                "APPROVED",
                1,
                0,
                json.dumps([]),
                json.dumps(sample_lines_1),
                "Sample AWS monthly enterprise compute bill",
                now_iso,
                now_iso
            ))

            sample_lines_2 = [
                {"description": "Enterprise Security Penetration Test", "quantity": 1, "unit_price": 4500.0, "total": 4500.0},
                {"description": "SOC 2 Type II Compliance Audit", "quantity": 1, "unit_price": 3000.0, "total": 3000.0}
            ]
            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, vendor_name, vendor_tax_id, invoice_date, due_date,
                    currency, subtotal, tax_amount, total_amount, status, is_reconciled,
                    has_anomalies, anomalies_json, line_items_json, raw_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "INV-2026-002",
                "SEC-8831-CORP",
                "CrowdStrike Incident Response Inc",
                "US-84910294",
                "2026-11-05",
                "2026-12-05",
                "USD",
                7500.0,
                600.0,
                8100.0,
                "PENDING_REVIEW",
                1,
                0,
                json.dumps([]),
                json.dumps(sample_lines_2),
                "Security compliance audit invoice",
                now_iso,
                now_iso
            ))

        conn.commit()
