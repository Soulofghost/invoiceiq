// InvoiceIQ Accounts Payable & Extraction Controller
const API_BASE = '/api/v1';

let currentExtractedData = null;

// DOM Elements
const statInvoices = document.getElementById('statInvoices');
const statSpend = document.getElementById('statSpend');
const statApprovedSpend = document.getElementById('statApprovedSpend');
const statPending = document.getElementById('statPending');
const statRecon = document.getElementById('statRecon');
const statAnomalies = document.getElementById('statAnomalies');
const refreshSummaryBtn = document.getElementById('refreshSummaryBtn');

const rawInvoiceInput = document.getElementById('rawInvoiceInput');
const extractForm = document.getElementById('extractForm');
const extractedResultCard = document.getElementById('extractedResultCard');

const extInvNum = document.getElementById('extInvNum');
const extVendor = document.getElementById('extVendor');
const extReconBadge = document.getElementById('extReconBadge');
const extDate = document.getElementById('extDate');
const extDueDate = document.getElementById('extDueDate');
const extTaxId = document.getElementById('extTaxId');
const extCurrency = document.getElementById('extCurrency');
const extItemsBody = document.getElementById('extItemsBody');
const extSubtotal = document.getElementById('extSubtotal');
const extTax = document.getElementById('extTax');
const extTotal = document.getElementById('extTotal');
const extAnomalyBox = document.getElementById('extAnomalyBox');
const saveInvoiceBtn = document.getElementById('saveInvoiceBtn');

const ledgerContainer = document.getElementById('ledgerContainer');
const statusFilter = document.getElementById('statusFilter');

// Sample Templates
const TEMPLATES = {
  AWS: `INVOICE #INV-AWS-2026-904
Date: 2026-11-04
Due Date: 2026-12-04
Vendor: Amazon Web Services Inc
Tax ID: US-4729104

Line Items:
Amazon EC2 Elastic Compute Cluster   10 x $150.00 = $1,500.00
Amazon Relational Database RDS Multi-AZ   2 x $250.00 = $500.00
Amazon S3 Standard Storage (Terabytes)   5 x $40.00 = $200.00

Subtotal: $2,200.00
Tax: $176.00
Total Due: $2,376.00`,

  DATADOG: `INVOICE #INV-DD-4491
Date: 2026-11-08
Due Date: 2026-12-08
From: Datadog Monitoring SAS
Tax ID: FR-88291049

APM Host Pro License   8 x $31.00 = $248.00
Log Ingestion Terabytes   2 x $105.00 = $210.00

Subtotal: $458.00
Tax: $36.64
Total: $494.64`,

  DISCREPANCY: `INVOICE #INV-ERR-8819
Date: 2026-11-01
From: Unverified Vendor Ltd
Tax ID: UNK-0000

Hardware Server Rack Units   2 x $1,000.00 = $2,000.00

Subtotal: $2,000.00
Tax: $850.00
Total: $3,500.00`
};

function loadTemplate(type) {
  if (TEMPLATES[type]) {
    rawInvoiceInput.value = TEMPLATES[type];
  }
}

// 1. Fetch Analytics Summary
async function fetchSummary() {
  try {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    if (!res.ok) throw new Error('Failed to load summary');
    const data = await res.json();

    statInvoices.textContent = data.total_invoices;
    statSpend.textContent = `$${data.total_spend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    statApprovedSpend.textContent = `Approved: $${data.approved_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    statPending.textContent = data.pending_approvals;
    statRecon.textContent = `${data.reconciliation_rate.toFixed(1)}%`;
    statAnomalies.textContent = data.anomalies_detected;
  } catch (err) {
    console.error('Error fetching summary:', err);
  }
}

// 2. Run Extraction Form
extractForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawText = rawInvoiceInput.value.trim();
  if (!rawText) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText })
    });

    if (!res.ok) throw new Error('Extraction failed');
    currentExtractedData = await res.json();
    renderExtractedCard(currentExtractedData);
  } catch (err) {
    alert(`Extraction error: ${err.message}`);
  }
});

function renderExtractedCard(data) {
  extInvNum.textContent = data.invoice_number;
  extVendor.textContent = data.vendor_name;
  extDate.textContent = data.invoice_date;
  extDueDate.textContent = data.due_date || 'N/A';
  extTaxId.textContent = data.vendor_tax_id || 'N/A';
  extCurrency.textContent = data.currency;

  if (data.is_reconciled) {
    extReconBadge.innerHTML = '<span class="badge-recon verified">✓ RECONCILED</span>';
  } else {
    extReconBadge.innerHTML = '<span class="badge-recon failed">⚠ ARITHMETIC MISMATCH</span>';
  }

  extItemsBody.innerHTML = data.line_items.map(item => `
    <tr>
      <td>${escapeHtml(item.description)}</td>
      <td>${item.quantity}</td>
      <td>$${item.unit_price.toFixed(2)}</td>
      <td><strong>$${item.total.toFixed(2)}</strong></td>
    </tr>
  `).join('');

  extSubtotal.textContent = `$${data.subtotal.toFixed(2)}`;
  extTax.textContent = `$${data.tax_amount.toFixed(2)}`;
  extTotal.textContent = `$${data.total_amount.toFixed(2)}`;

  if (data.has_anomalies && data.anomalies.length > 0) {
    extAnomalyBox.classList.remove('hidden');
    extAnomalyBox.innerHTML = `<strong>Attention Required:</strong><ul>${data.anomalies.map(a => `<li>${escapeHtml(a)}</li>`).join('')}</ul>`;
  } else {
    extAnomalyBox.classList.add('hidden');
  }

  extractedResultCard.classList.remove('hidden');
}

// Save Invoice to Ledger
saveInvoiceBtn.addEventListener('click', async () => {
  if (!currentExtractedData) return;

  try {
    const res = await fetch(`${API_BASE}/invoices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        invoice_number: currentExtractedData.invoice_number,
        vendor_name: currentExtractedData.vendor_name,
        vendor_tax_id: currentExtractedData.vendor_tax_id,
        invoice_date: currentExtractedData.invoice_date,
        due_date: currentExtractedData.due_date,
        currency: currentExtractedData.currency,
        subtotal: currentExtractedData.subtotal,
        tax_amount: currentExtractedData.tax_amount,
        total_amount: currentExtractedData.total_amount,
        line_items: currentExtractedData.line_items,
        raw_text: rawInvoiceInput.value
      })
    });

    if (!res.ok) throw new Error('Failed to record invoice');
    alert('Invoice successfully saved to Accounts Payable Ledger!');
    extractedResultCard.classList.add('hidden');
    rawInvoiceInput.value = '';
    currentExtractedData = null;

    fetchSummary();
    fetchInvoices();
  } catch (err) {
    alert(`Save error: ${err.message}`);
  }
});

// 3. Fetch Invoices Ledger
async function fetchInvoices() {
  const status = statusFilter.value;
  const url = status ? `${API_BASE}/invoices?status=${status}` : `${API_BASE}/invoices`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load ledger');
    const invoices = await res.json();

    if (invoices.length === 0) {
      ledgerContainer.innerHTML = '<div class="empty-state">No invoices match selected criteria.</div>';
      return;
    }

    ledgerContainer.innerHTML = invoices.map(inv => {
      const statusClass = `status-${inv.status.toLowerCase()}`;
      return `
        <div class="invoice-card">
          <div class="inv-main">
            <span class="inv-num font-mono text-cyan">${escapeHtml(inv.invoice_number)}</span>
            <span class="inv-vendor">${escapeHtml(inv.vendor_name)}</span>
            <span class="inv-meta">
              DATE: ${inv.invoice_date} | ITEMS: ${inv.line_items.length} | RECON: 
              <strong class="${inv.is_reconciled ? 'text-emerald' : 'text-coral'}">
                ${inv.is_reconciled ? 'PASSED' : 'MISMATCH'}
              </strong>
            </span>
          </div>
          <div class="inv-finance">
            <span class="inv-amount font-mono">$${inv.total_amount.toFixed(2)}</span>
            <span class="status-pill ${statusClass}">${inv.status}</span>
            <div style="display:flex; gap:0.4rem; margin-top:0.3rem;">
              ${inv.status === 'PENDING_REVIEW' ? 
                `<button class="btn btn-xs btn-emerald" onclick="updateStatus('${inv.id}', 'APPROVED')">Approve</button>` : ''}
              ${inv.status === 'APPROVED' ? 
                `<button class="btn btn-xs btn-primary" onclick="updateStatus('${inv.id}', 'PAID')">Mark Paid</button>` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error fetching invoices:', err);
  }
}

async function updateStatus(invId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/invoices/${invId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error('Status transition failed');
    fetchInvoices();
    fetchSummary();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

statusFilter.addEventListener('change', fetchInvoices);
refreshSummaryBtn.addEventListener('click', () => {
  fetchSummary();
  fetchInvoices();
});

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Initial Boot
loadTemplate('AWS');
fetchSummary();
fetchInvoices();
