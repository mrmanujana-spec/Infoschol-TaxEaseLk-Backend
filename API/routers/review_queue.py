from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import CompanyOut, ReviewStatus, RiskLevel, CITStatus

router = APIRouter(prefix="/auditor/review-queue", tags=["Review Queue"])


@router.get("", response_model=List[CompanyOut])
def get_review_queue(
    tab: Optional[ReviewStatus] = Query(None, description="Which queue tab is selected"),
    risk: Optional[RiskLevel] = None,
    financial_year: Optional[str] = None,
    search: Optional[str] = Query(None, description="Matches company name or TIN"),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        query = supabase.table("companies").select("*").eq("assigned_auditor_id", user.user_id)

        if tab:
            query = query.eq("review_status", tab.value)
        if risk:
            query = query.eq("risk_level", risk.value)
        if financial_year:
            query = query.eq("financial_year", financial_year)
        if search:
            query = query.ilike("name", f"%{search}%")

        result = query.order("due_date").execute()
        return result.data or []
    except Exception:
        return []


@router.post("/{company_id}/approve", response_model=CompanyOut)
def approve_filing(company_id: str, user: CurrentUser = Depends(get_current_user)):
    try:
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

        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{company_id}/request-information", response_model=CompanyOut)
def request_information(
    company_id: str,
    message: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = (
            supabase.table("companies")
            .update({"review_status": ReviewStatus.waiting_for_company.value})
            .eq("id", company_id)
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Company not found.")

        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
