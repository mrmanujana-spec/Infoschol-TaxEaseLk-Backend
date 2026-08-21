"""
Matches: Review Queue screen
Tabs on screen: All, Pending, In Progress, Waiting for Company,
Ready for Approval, Completed
Filters: Risk, Status, Financial Year, Due Date, Search company/issue
Columns: Company, Status, Critical, Warnings, Progress, Due

This reuses the "companies" table (same data as the Companies screen)
but filtered/shaped for the review workflow, plus the two actions this
screen triggers: approve, and request more info from the company.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import CompanyOut, ReviewStatus, RiskLevel, CITStatus
from app.utils import log_action

router = APIRouter(prefix="/auditor/review-queue", tags=["Review Queue"])


@router.get("", response_model=List[CompanyOut])
def get_review_queue(
    tab: Optional[ReviewStatus] = Query(None, description="Which queue tab is selected"),
    risk: Optional[RiskLevel] = None,
    financial_year: Optional[str] = None,
    search: Optional[str] = Query(None, description="Matches company name or an issue title"),
    user: CurrentUser = Depends(require_role("auditor")),
):
    query = supabase.table("companies").select("*").eq("assigned_auditor_id", user.user_id)

    if tab:  # "All" tab = don't filter by review_status
        query = query.eq("review_status", tab.value)
    if risk:
        query = query.eq("risk_level", risk.value)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if search:
        query = query.ilike("name", f"%{search}%")

    result = query.order("due_date").execute()
    return result.data


@router.post("/{company_id}/approve", response_model=CompanyOut)
def approve_filing(company_id: str, user: CurrentUser = Depends(require_role("auditor"))):
    result = (
        supabase.table("companies")
        .update(
            {
                "review_status": ReviewStatus.completed.value,
                "cit_status": CITStatus.approved.value,
                "progress_percent": 100,
            }
        )
        .eq("id", company_id)
        .eq("assigned_auditor_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found.")

    log_action(
        company_id=company_id,
        user_type="Auditor",
        user_name=user.email,
        action="CIT Computation Approved",
        details="Final approval granted.",
    )
    return result.data[0]


@router.post("/{company_id}/request-information", response_model=CompanyOut)
def request_information(
    company_id: str,
    message: str,
    user: CurrentUser = Depends(require_role("auditor")),
):
    result = (
        supabase.table("companies")
        .update({"review_status": ReviewStatus.waiting_for_company.value})
        .eq("id", company_id)
        .eq("assigned_auditor_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found.")

    log_action(
        company_id=company_id,
        user_type="Auditor",
        user_name=user.email,
        action="Information Requested",
        details=message,
    )
    return result.data[0]
