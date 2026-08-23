import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from database import get_db, Business, ExtractedValue, Document, DocumentHistory
from auth import get_current_business

router = APIRouter(prefix="/financials", tags=["Financials"])


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class FinancialValueUpdate(BaseModel):
    value:  str
    reason: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_values_by_category(db: Session, business_id: int, financial_year_id: Optional[int], category: str):
    """Get extracted values for a specific category filtered by business."""
    query = (
        db.query(ExtractedValue)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(
            Document.business_id == business_id,
            ExtractedValue.field_name.ilike(f"%{category}%"),
        )
    )
    if financial_year_id:
        query = query.filter(Document.financial_year_id == financial_year_id)
    return query.all()


def get_all_values(db: Session, business_id: int, financial_year_id: Optional[int]):
    """Get all extracted values for a business."""
    query = (
        db.query(ExtractedValue)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(Document.business_id == business_id)
    )
    if financial_year_id:
        query = query.filter(Document.financial_year_id == financial_year_id)
    return query.all()


def format_value(v: ExtractedValue):
    return {
        "id":         v.id,
        "field_name": v.field_name,
        "value":      v.value,
        "confidence": v.confidence,
        "page":       v.page,
        "notes":      v.notes,
        "document_id":v.document_id,
        "created_at": v.created_at,
    }


def get_value_or_404(db: Session, value_id: int, business_id: int) -> ExtractedValue:
    v = (
        db.query(ExtractedValue)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(
            ExtractedValue.id == value_id,
            Document.business_id == business_id,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail=f"Financial value {value_id} not found.")
    return v


# ─── GET /financials/summary ──────────────────────────────────────────────────

@router.get("/summary")
def get_financials_summary(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get Revenue, Expenses, Accounting Profit, and Tax Adjustments."""
    values = get_all_values(db, current_business.id, financial_year_id)

    def get_val(name):
        for v in values:
            if v.field_name == name:
                try:
                    return float(v.value)
                except:
                    return 0.0
        return 0.0

    total_revenue   = get_val("total_revenue")
    total_expenses  = get_val("total_expenses")
    accounting_profit = get_val("accounting_profit") or (total_revenue - total_expenses)
    tax_paid        = get_val("tax_paid")

    # Tax adjustments
    tax_adjustments = accounting_profit * 0.30  # 30% CIT rate for Sri Lanka

    return {
        "financial_year_id":  financial_year_id,
        "revenue": {
            "label": "Total Revenue",
            "value": total_revenue,
        },
        "expenses": {
            "label": "Total Expenses",
            "value": total_expenses,
        },
        "accounting_profit": {
            "label": "Accounting Profit",
            "value": accounting_profit,
        },
        "tax_adjustments": {
            "label": "Tax Adjustments (CIT @ 30%)",
            "value": round(tax_adjustments, 2),
        },
        "tax_paid": {
            "label": "Tax Paid",
            "value": tax_paid,
        },
        "total_values": len(values),
    }


# ─── GET /financials/income-statement ────────────────────────────────────────

@router.get("/income-statement")
def get_income_statement(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get income statement values extracted from documents."""
    income_fields = [
        "total_revenue", "gross_profit", "operating_income",
        "other_income", "total_expenses", "operating_expenses",
        "accounting_profit", "net_profit", "tax_paid", "profit_after_tax"
    ]

    all_values = get_all_values(db, current_business.id, financial_year_id)
    income_values = [v for v in all_values if v.field_name in income_fields]

    return {
        "financial_year_id": financial_year_id,
        "statement_type":    "income_statement",
        "total":             len(income_values),
        "values":            [format_value(v) for v in income_values],
    }


# ─── GET /financials/balance-sheet ───────────────────────────────────────────

@router.get("/balance-sheet")
def get_balance_sheet(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get balance sheet values extracted from documents."""
    balance_fields = [
        "total_assets", "current_assets", "fixed_assets", "intangible_assets",
        "total_liabilities", "current_liabilities", "long_term_liabilities",
        "total_equity", "retained_earnings", "share_capital"
    ]

    all_values = get_all_values(db, current_business.id, financial_year_id)
    balance_values = [v for v in all_values if v.field_name in balance_fields]

    return {
        "financial_year_id": financial_year_id,
        "statement_type":    "balance_sheet",
        "total":             len(balance_values),
        "values":            [format_value(v) for v in balance_values],
    }


# ─── GET /financials/trial-balance ───────────────────────────────────────────

@router.get("/trial-balance")
def get_trial_balance(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get trial balance values extracted from documents."""
    all_values = get_all_values(db, current_business.id, financial_year_id)

    debit_fields  = ["total_assets", "total_expenses", "current_assets", "fixed_assets"]
    credit_fields = ["total_revenue", "total_liabilities", "total_equity", "share_capital"]

    debit_values  = [v for v in all_values if v.field_name in debit_fields]
    credit_values = [v for v in all_values if v.field_name in credit_fields]

    total_debits  = sum(float(v.value) for v in debit_values  if v.value)
    total_credits = sum(float(v.value) for v in credit_values if v.value)

    return {
        "financial_year_id": financial_year_id,
        "statement_type":    "trial_balance",
        "debits": {
            "values": [format_value(v) for v in debit_values],
            "total":  round(total_debits, 2),
        },
        "credits": {
            "values": [format_value(v) for v in credit_values],
            "total":  round(total_credits, 2),
        },
        "is_balanced": abs(total_debits - total_credits) < 0.01,
    }


# ─── GET /financials/general-ledger ──────────────────────────────────────────

@router.get("/general-ledger")
def get_general_ledger(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get all general ledger values grouped by document."""
    query = (
        db.query(ExtractedValue, Document)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(Document.business_id == current_business.id)
    )
    if financial_year_id:
        query = query.filter(Document.financial_year_id == financial_year_id)

    results = query.all()

    # Group by document
    ledger = {}
    for v, doc in results:
        if doc.id not in ledger:
            ledger[doc.id] = {
                "document_id":   doc.id,
                "document_name": doc.name,
                "doc_type":      doc.doc_type,
                "entries":       [],
            }
        ledger[doc.id]["entries"].append(format_value(v))

    return {
        "financial_year_id": financial_year_id,
        "statement_type":    "general_ledger",
        "total_documents":   len(ledger),
        "ledger":            list(ledger.values()),
    }


# ─── GET /financials/fixed-assets ────────────────────────────────────────────

@router.get("/fixed-assets")
def get_fixed_assets(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get fixed asset values extracted from documents."""
    asset_fields = [
        "fixed_assets", "total_assets", "intangible_assets",
        "land_and_buildings", "plant_and_machinery", "furniture_and_fittings",
        "motor_vehicles", "computer_equipment", "accumulated_depreciation",
        "net_book_value"
    ]

    all_values = get_all_values(db, current_business.id, financial_year_id)
    asset_values = [v for v in all_values if v.field_name in asset_fields]

    total_fixed_assets = sum(
        float(v.value) for v in asset_values
        if v.field_name in ["fixed_assets", "total_assets"] and v.value
    )

    return {
        "financial_year_id": financial_year_id,
        "statement_type":    "fixed_assets",
        "total_fixed_assets": round(total_fixed_assets, 2),
        "total":             len(asset_values),
        "values":            [format_value(v) for v in asset_values],
    }


# ─── GET /financials/values/{value_id} ───────────────────────────────────────

@router.get("/values/{value_id}")
def get_financial_value(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get one financial value for the Edit Financial Value modal."""
    v   = get_value_or_404(db, value_id, current_business.id)
    doc = db.query(Document).filter(Document.id == v.document_id).first()

    return {
        "id":            v.id,
        "field_name":    v.field_name,
        "value":         v.value,
        "confidence":    v.confidence,
        "page":          v.page,
        "notes":         v.notes,
        "document_id":   v.document_id,
        "document_name": doc.name if doc else None,
        "doc_type":      doc.doc_type if doc else None,
        "created_at":    v.created_at,
    }


# ─── PATCH /financials/values/{value_id} ─────────────────────────────────────

@router.patch("/values/{value_id}")
def update_financial_value(
    value_id: int,
    payload:  FinancialValueUpdate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Save a corrected financial value and the reason for the change."""
    v = get_value_or_404(db, value_id, current_business.id)

    old_value = v.value

    # Update value
    v.value = payload.value
    v.notes = payload.reason

    # Log to document history
    doc = db.query(Document).filter(Document.id == v.document_id).first()
    history = DocumentHistory(
        document_id = v.document_id,
        event       = "value_corrected",
        message     = f"Field '{v.field_name}' changed from '{old_value}' to '{payload.value}'. Reason: {payload.reason}",
        created_at  = datetime.utcnow(),
    )
    db.add(history)
    db.commit()
    db.refresh(v)

    return {
        "message":   "Financial value updated successfully.",
        "id":        v.id,
        "field_name":v.field_name,
        "old_value": old_value,
        "new_value": v.value,
        "reason":    payload.reason,
        "updated_at":datetime.utcnow(),
    }


# ─── GET /financials/values/{value_id}/source ─────────────────────────────────

@router.get("/values/{value_id}/source")
def get_value_source(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """View the original source document and page where value was extracted."""
    v   = get_value_or_404(db, value_id, current_business.id)
    doc = db.query(Document).filter(Document.id == v.document_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Source document not found.")

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Source file not found on server.")

    return FileResponse(
        path      = doc.file_path,
        media_type= doc.file_type or "application/octet-stream",
        filename  = doc.file_name,
        headers   = {"X-Page-Number": str(v.page or 1)},
    )


# ─── GET /financials/values/{value_id}/history ────────────────────────────────

@router.get("/values/{value_id}/history")
def get_value_history(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get the full audit history of changes to a financial value."""
    v   = get_value_or_404(db, value_id, current_business.id)
    doc = db.query(Document).filter(Document.id == v.document_id).first()

    history = (
        db.query(DocumentHistory)
        .filter(
            DocumentHistory.document_id == v.document_id,
            DocumentHistory.event       == "value_corrected",
            DocumentHistory.message.ilike(f"%{v.field_name}%"),
        )
        .order_by(DocumentHistory.created_at.desc())
        .all()
    )

    return {
        "value_id":      value_id,
        "field_name":    v.field_name,
        "current_value": v.value,
        "document_id":   v.document_id,
        "document_name": doc.name if doc else None,
        "total_changes": len(history),
        "history": [
            {
                "id":         h.id,
                "event":      h.event,
                "message":    h.message,
                "created_at": h.created_at,
            }
            for h in history
        ],
    }