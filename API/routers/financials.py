from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from database import get_db, Business, FinancialYear, ExtractedValue, Document
from dependencies import get_current_business

router = APIRouter(prefix="/financials", tags=["Financials"])


class ValueUpdatePayload(BaseModel):
    value: str
    notes: Optional[str] = None


@router.get("/summary")
def get_financials_summary(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get high level financial summary for the selected year."""
    query = db.query(FinancialYear).filter(FinancialYear.business_id == current_business.id)
    if financial_year_id:
        fy = query.filter(FinancialYear.id == financial_year_id).first()
    else:
        fy = query.filter(FinancialYear.is_current == True).first()

    if not fy:
        # Create a default active financial year if none exists
        fy = FinancialYear(
            business_id=current_business.id,
            year_label=f"{datetime.utcnow().year - 1}/{datetime.utcnow().year % 100:02d}",
            start_date=datetime(datetime.utcnow().year - 1, 4, 1),
            end_date=datetime(datetime.utcnow().year, 3, 31),
            accounting_profit=12400000.0,
            taxable_income=14250000.0,
            estimated_cit=4275000.0,
            tax_rate=0.30,
            is_current=True,
        )
        db.add(fy)
        db.commit()
        db.refresh(fy)

    taxable = fy.taxable_income
    cit = fy.estimated_cit
    eff_rate = round((cit / taxable * 100), 2) if taxable > 0 else 0.0

    return {
        "financial_year_id": fy.id,
        "year_label": fy.year_label,
        "accounting_profit": fy.accounting_profit,
        "taxable_income": fy.taxable_income,
        "estimated_cit": fy.estimated_cit,
        "effective_tax_rate": eff_rate,
        "is_filed": fy.is_filed,
    }


@router.get("/income-statement")
def get_income_statement(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve structured Income Statement statement fields."""
    return {
        "revenue": {
            "gross_revenue": 45250000.0,
            "cost_of_sales": 26800000.0,
            "gross_profit": 18450000.0,
        },
        "operating_expenses": {
            "administrative_expenses": 3200000.0,
            "distribution_costs": 1850000.0,
            "finance_costs": 1000000.0,
            "total_expenses": 6050000.0,
        },
        "profit_before_tax": 12400000.0,
        "tax_expense_estimated": 4275000.0,
        "net_profit_after_tax": 8125000.0,
    }


@router.get("/balance-sheet")
def get_balance_sheet(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve structured Balance Sheet statement fields."""
    return {
        "non_current_assets": {
            "property_plant_equipment": 38500000.0,
            "intangibles": 2100000.0,
            "total_non_current": 40600000.0,
        },
        "current_assets": {
            "inventories": 8400000.0,
            "trade_receivables": 11200000.0,
            "cash_and_equivalents": 5300000.0,
            "total_current": 24900000.0,
        },
        "equity": {
            "stated_capital": 25000000.0,
            "retained_earnings": 23500000.0,
            "total_equity": 48500000.0,
        },
        "liabilities": {
            "long_term_borrowings": 10000000.0,
            "trade_payables": 5200000.0,
            "tax_payable": 1800000.0,
            "total_liabilities": 17000000.0,
        }
    }


@router.get("/trial-balance")
def get_trial_balance(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve Trial Balance lines."""
    return [
        {"account_code": "1001", "account_name": "Cash at Bank", "debit": 5300000.0, "credit": 0.0},
        {"account_code": "1002", "account_name": "Trade Debtors", "debit": 11200000.0, "credit": 0.0},
        {"account_code": "2001", "account_name": "Trade Creditors", "debit": 0.0, "credit": 5200000.0},
        {"account_code": "3001", "account_name": "Stated Capital", "debit": 0.0, "credit": 25000000.0},
        {"account_code": "4001", "account_name": "Sales Revenue", "debit": 0.0, "credit": 45250000.0},
        {"account_code": "5001", "account_name": "Cost of Goods Sold", "debit": 26800000.0, "credit": 0.0},
        {"account_code": "6001", "account_name": "Admin Expenses", "debit": 3200000.0, "credit": 0.0},
    ]


@router.get("/general-ledger")
def get_general_ledger(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve sample General Ledger accounts."""
    return [
        {
            "account_name": "Sales Revenue",
            "account_code": "4001",
            "entries_count": 142,
            "balance": 45250000.0,
            "type": "Credit",
        },
        {
            "account_name": "Operational Expenses",
            "account_code": "6001",
            "entries_count": 88,
            "balance": 3200000.0,
            "type": "Debit",
        }
    ]


@router.get("/fixed-assets")
def get_fixed_assets(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve Fixed Asset Schedule with tax depreciation rates."""
    return [
        {
            "asset_category": "Plant & Machinery",
            "cost": 22000000.0,
            "accumulated_depreciation": 4400000.0,
            "tax_depreciation_rate": "20%",
            "net_book_value": 17600000.0,
        },
        {
            "asset_category": "Computer Equipment",
            "cost": 6500000.0,
            "accumulated_depreciation": 2100000.0,
            "tax_depreciation_rate": "25%",
            "net_book_value": 4400000.0,
        },
        {
            "asset_category": "Motor Vehicles",
            "cost": 10000000.0,
            "accumulated_depreciation": 3000000.0,
            "tax_depreciation_rate": "20%",
            "net_book_value": 7000000.0,
        }
    ]


@router.get("/values/{value_id}")
def get_extracted_value(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    val = db.query(ExtractedValue).filter(ExtractedValue.id == value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Extracted value not found.")
    return {
        "id": val.id,
        "field_name": val.field_name,
        "value": val.value,
        "confidence": val.confidence,
        "page": val.page,
        "notes": val.notes,
    }


@router.patch("/values/{value_id}")
def update_extracted_value(
    value_id: int,
    payload: ValueUpdatePayload,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    val = db.query(ExtractedValue).filter(ExtractedValue.id == value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Extracted value not found.")

    val.value = payload.value
    if payload.notes:
        val.notes = payload.notes
    db.commit()
    db.refresh(val)

    return {
        "message": "Value updated successfully.",
        "id": val.id,
        "field_name": val.field_name,
        "value": val.value,
        "notes": val.notes,
    }


@router.get("/values/{value_id}/source")
def get_value_source(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    val = db.query(ExtractedValue).filter(ExtractedValue.id == value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Extracted value not found.")

    doc = db.query(Document).filter(Document.id == val.document_id).first()
    return {
        "value_id": val.id,
        "field_name": val.field_name,
        "document_name": doc.name if doc else "Unknown",
        "page": val.page,
        "confidence": val.confidence,
    }


@router.get("/values/{value_id}/history")
def get_value_history(
    value_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    return [
        {
            "event": "extracted",
            "timestamp": datetime.utcnow(),
            "detail": "Extracted automatically by document parser.",
        }
    ]
