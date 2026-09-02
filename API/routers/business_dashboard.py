from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import cast

from database import (
    get_db, Business, FinancialYear, Document, ActionRequired, IssueStatusEnum
)
from dependencies import get_current_business
from schemas import DashboardOut, DocumentProgress

router = APIRouter(prefix="/business", tags=["Business Dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def get_business_dashboard(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve high-level overview metrics for the business dashboard."""
    bid = current_business.id

    # Get current financial year
    current_fy = db.query(FinancialYear).filter(
        FinancialYear.business_id == bid,
        FinancialYear.is_current == True,
    ).first()

    # Document stats
    all_docs = db.query(Document).filter(Document.business_id == bid).all()
    total_docs = len(all_docs)
    uploaded_docs = sum(1 for d in all_docs if cast(bool, d.is_uploaded))
    progress_pct = int(round((uploaded_docs / total_docs * 100))) if total_docs > 0 else 0

    # Unresolved issues
    open_issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == bid,
        ActionRequired.status == IssueStatusEnum.open,
    ).count()

    doc_progress = DocumentProgress(
        uploaded=uploaded_docs,
        total=total_docs,
        label=f"{uploaded_docs} of {total_docs} Uploaded",
        percent=float(progress_pct),
        percentage=float(progress_pct),
    )

    auditor_status_val = (
        current_business.auditor_status.value
        if hasattr(current_business.auditor_status, "value")
        else str(current_business.auditor_status)
    )

    return DashboardOut(
        progress=progress_pct,
        documents=doc_progress,
        accounting_profit=(
            cast(float, current_fy.accounting_profit)
            if current_fy is not None
            else 0.0
        ),
        taxable_income=(
            cast(float, current_fy.taxable_income)
            if current_fy is not None
            else 0.0
        ),
        estimated_cit=(
            cast(float, current_fy.estimated_cit)
            if current_fy is not None
            else 0.0
        ),
        auditor_status=auditor_status_val,
        requires_attention=open_issues,
    )
