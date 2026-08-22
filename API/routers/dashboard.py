import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
try:
    from ..database import get_db, Business, Document, ActionRequired, FinancialYear, IssueStatusEnum
    from ..auth import get_current_business
    from ..schemas import DashboardOut, DocumentProgress
except ImportError:
    from database import get_db, Business, Document, ActionRequired, FinancialYear, IssueStatusEnum
    from auth import get_current_business
    from schemas import DashboardOut, DocumentProgress

router = APIRouter(prefix="/business", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    business_id = current_business.id

    all_docs      = db.query(Document).filter(Document.business_id == business_id).all()
    total_docs    = len(all_docs)
    uploaded_docs = sum(1 for d in all_docs if d.is_uploaded)
    doc_percent   = round((uploaded_docs / total_docs * 100), 1) if total_docs > 0 else 0.0

    current_fy = (
        db.query(FinancialYear)
        .filter(FinancialYear.business_id == business_id, FinancialYear.is_current == True)
        .first()
    )

    accounting_profit = current_fy.accounting_profit if current_fy else 0.0
    taxable_income    = current_fy.taxable_income    if current_fy else 0.0
    estimated_cit     = current_fy.estimated_cit     if current_fy else 0.0

    open_issues_count = (
        db.query(ActionRequired)
        .filter(ActionRequired.business_id == business_id, ActionRequired.status == IssueStatusEnum.open)
        .count()
    )

    doc_score        = doc_percent * 0.5
    issue_score      = 50.0 if open_issues_count == 0 else max(0, 50 - open_issues_count * 5)
    overall_progress = min(100, int(doc_score + issue_score))

    return DashboardOut(
        progress           = overall_progress,
        documents          = DocumentProgress(
            uploaded = uploaded_docs,
            total    = total_docs,
            label    = f"{uploaded_docs}/{total_docs}",
            percent  = doc_percent,
        ),
        accounting_profit  = accounting_profit,
        taxable_income     = taxable_income,
        estimated_cit      = estimated_cit,
        auditor_status     = current_business.auditor_status,
        requires_attention = open_issues_count,
    )


