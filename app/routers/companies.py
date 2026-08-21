"""
Matches: Companies screen
Columns on screen: Company, TIN, Financial Year, CIT Status, Issues,
Progress, Due Date, Actions
Filters on screen: Search, Status, Financial Year, Review Status, Risk Level
Buttons on screen: Import Companies, Add Company

Assumes a Supabase table "companies" with columns:
  id (uuid), name, tin (unique), financial_year, cit_status, review_status,
  risk_level, progress_percent (int, default 0), due_date, assigned_auditor_id,
  critical_issues_count (int, default 0), warnings_count (int, default 0),
  created_at
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyOut,
    CompanyImportRequest,
    CITStatus,
    ReviewStatus,
    RiskLevel,
)

router = APIRouter(prefix="/auditor/companies", tags=["Companies"])


@router.get("", response_model=List[CompanyOut])
def list_companies(
    search: Optional[str] = Query(None, description="Matches company name or TIN"),
    cit_status: Optional[CITStatus] = None,
    financial_year: Optional[str] = None,
    review_status: Optional[ReviewStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    user: CurrentUser = Depends(require_role("auditor")),
):
    query = supabase.table("companies").select("*").eq("assigned_auditor_id", user.user_id)

    if cit_status:
        query = query.eq("cit_status", cit_status.value)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if review_status:
        query = query.eq("review_status", review_status.value)
    if risk_level:
        query = query.eq("risk_level", risk_level.value)
    if search:
        # matches company name OR TIN containing the search text
        query = query.or_(f"name.ilike.%{search}%,tin.ilike.%{search}%")

    result = query.order("due_date").execute()
    return result.data


@router.post("", response_model=CompanyOut, status_code=201)
def add_company(company: CompanyCreate, user: CurrentUser = Depends(require_role("auditor"))):
    payload = company.model_dump(mode="json", exclude_none=True)
    payload["assigned_auditor_id"] = user.user_id
    payload["cit_status"] = CITStatus.draft.value
    payload["review_status"] = ReviewStatus.not_started.value
    payload["progress_percent"] = 0
    payload["critical_issues_count"] = 0
    payload["warnings_count"] = 0

    result = supabase.table("companies").insert(payload).execute()
    return result.data[0]


@router.post("/import", response_model=List[CompanyOut], status_code=201)
def import_companies(
    request: CompanyImportRequest, user: CurrentUser = Depends(require_role("auditor"))
):
    """Bulk version of 'Add Company' -- for the 'Import Companies' button."""
    rows = []
    for company in request.companies:
        payload = company.model_dump(mode="json", exclude_none=True)
        payload["assigned_auditor_id"] = user.user_id
        payload["cit_status"] = CITStatus.draft.value
        payload["review_status"] = ReviewStatus.not_started.value
        payload["progress_percent"] = 0
        payload["critical_issues_count"] = 0
        payload["warnings_count"] = 0
        rows.append(payload)

    if not rows:
        raise HTTPException(status_code=400, detail="No companies provided.")

    result = supabase.table("companies").insert(rows).execute()
    return result.data


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, user: CurrentUser = Depends(require_role("auditor"))):
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


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    updates: CompanyUpdate,
    user: CurrentUser = Depends(require_role("auditor")),
):
    payload = {k: v for k, v in updates.model_dump(mode="json").items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = (
        supabase.table("companies")
        .update(payload)
        .eq("id", company_id)
        .eq("assigned_auditor_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found.")
    return result.data[0]


@router.delete("/{company_id}", status_code=204)
def remove_company(company_id: str, user: CurrentUser = Depends(require_role("auditor"))):
    result = (
        supabase.table("companies")
        .delete()
        .eq("id", company_id)
        .eq("assigned_auditor_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found.")
