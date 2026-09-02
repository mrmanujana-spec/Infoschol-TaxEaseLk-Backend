from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyOut,
    CompanyImportRequest,
    CITStatus,
    ReviewStatus,
    RiskLevel,
    MessageOut,
)

router = APIRouter(prefix="/auditor/companies", tags=["Companies"])


@router.get("", response_model=List[CompanyOut])
def get_companies(
    cit_status: Optional[CITStatus] = None,
    review_status: Optional[ReviewStatus] = None,
    risk: Optional[RiskLevel] = None,
    financial_year: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search by name or TIN"),
    sort_by: Optional[str] = Query("name", description="Column to sort by"),
    sort_dir: Optional[str] = Query("asc", description="asc or desc"),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        query = supabase.table("companies").select("*").eq("assigned_auditor_id", user.user_id)

        if cit_status:
            query = query.eq("cit_status", cit_status.value)
        if review_status:
            query = query.eq("review_status", review_status.value)
        if risk:
            query = query.eq("risk_level", risk.value)
        if financial_year:
            query = query.eq("financial_year", financial_year)
        if search:
            query = query.or_(f"name.ilike.%{search}%,tin.ilike.%{search}%")

        query = query.order(sort_by, desc=(sort_dir == "desc"))
        result = query.execute()
        return result.data or []
    except Exception:
        return []


@router.post("", response_model=CompanyOut, status_code=201)
def add_company(
    payload: CompanyCreate,
    user: CurrentUser = Depends(get_current_user),
):
    row = {
        "assigned_auditor_id": user.user_id,
        "name": payload.name,
        "tin": payload.tin,
        "financial_year": payload.financial_year,
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "risk_level": payload.risk_level.value if payload.risk_level else None,
        "cit_status": CITStatus.draft.value,
        "review_status": ReviewStatus.not_started.value,
        "progress_percent": 0,
        "critical_issues_count": 0,
        "warnings_count": 0,
    }
    try:
        result = supabase.table("companies").insert(row).execute()
        if not result.data:
            raise HTTPException(status_code=400, detail="Could not create company.")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import", response_model=List[CompanyOut], status_code=201)
def import_companies(
    payload: CompanyImportRequest,
    user: CurrentUser = Depends(get_current_user),
):
    rows = [
        {
            "assigned_auditor_id": user.user_id,
            "name": c.name,
            "tin": c.tin,
            "financial_year": c.financial_year,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "risk_level": c.risk_level.value if c.risk_level else None,
            "cit_status": CITStatus.draft.value,
            "review_status": ReviewStatus.not_started.value,
            "progress_percent": 0,
            "critical_issues_count": 0,
            "warnings_count": 0,
        }
        for c in payload.companies
    ]
    try:
        result = supabase.table("companies").insert(rows).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("companies")
            .select("*")
            .eq("id", company_id)
            .eq("assigned_auditor_id", user.user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Company not found.")
        return result.data
    except Exception:
        raise HTTPException(status_code=404, detail="Company not found.")


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    payload: CompanyUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    updates = {}
    if payload.cit_status is not None:
        updates["cit_status"] = payload.cit_status.value
    if payload.review_status is not None:
        updates["review_status"] = payload.review_status.value
    if payload.risk_level is not None:
        updates["risk_level"] = payload.risk_level.value
    if payload.progress_percent is not None:
        updates["progress_percent"] = payload.progress_percent
    if payload.due_date is not None:
        updates["due_date"] = payload.due_date.isoformat()

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    try:
        result = (
            supabase.table("companies")
            .update(updates)
            .eq("id", company_id)
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Company not found.")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{company_id}", response_model=MessageOut)
def delete_company(company_id: str, user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("companies")
            .delete()
            .eq("id", company_id)
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Company not found.")
        return {"message": "Company deleted."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
