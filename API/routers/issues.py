from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import (
    IssueOut,
    IssueResolve,
    IssueSummaryOut,
    IssueSeverity,
    IssueStatus,
    MessageOut,
)

router = APIRouter(prefix="/auditor/issues", tags=["Issues"])


def _get_my_company_ids(auditor_id: str) -> List[str]:
    try:
        res = (
            supabase.table("companies")
            .select("id")
            .eq("assigned_auditor_id", auditor_id)
            .execute()
        )
        return [c["id"] for c in (res.data or [])]
    except Exception:
        return []


@router.get("/summary", response_model=IssueSummaryOut)
def get_issue_summary(
    company_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    my_company_ids = [company_id] if company_id else _get_my_company_ids(user.user_id)
    if not my_company_ids:
        return {"critical": 0, "warnings": 0, "information": 0, "resolved": 0}

    try:
        res = (
            supabase.table("issues")
            .select("severity, status")
            .in_("company_id", my_company_ids)
            .execute()
        )
        data = res.data or []
        critical = sum(
            1 for i in data if i.get("severity") == IssueSeverity.critical.value and i.get("status") == IssueStatus.open.value
        )
        warnings = sum(
            1 for i in data if i.get("severity") == IssueSeverity.warning.value and i.get("status") == IssueStatus.open.value
        )
        info = sum(
            1 for i in data if i.get("severity") == IssueSeverity.info.value and i.get("status") == IssueStatus.open.value
        )
        resolved = sum(1 for i in data if i.get("status") == IssueStatus.resolved.value)

        return {
            "critical": critical,
            "warnings": warnings,
            "information": info,
            "resolved": resolved,
        }
    except Exception:
        return {"critical": 0, "warnings": 0, "information": 0, "resolved": 0}


@router.get("", response_model=List[IssueOut])
def get_issues(
    company_id: Optional[str] = None,
    severity: Optional[IssueSeverity] = None,
    status: Optional[IssueStatus] = None,
    user: CurrentUser = Depends(get_current_user),
):
    my_company_ids = [company_id] if company_id else _get_my_company_ids(user.user_id)
    if not my_company_ids:
        return []

    try:
        query = (
            supabase.table("issues")
            .select("id, company_id, title, amount, severity, status, source, created_at, companies(name)")
            .in_("company_id", my_company_ids)
        )

        if severity:
            query = query.eq("severity", severity.value)
        if status:
            query = query.eq("status", status.value)

        result = query.order("created_at", desc=True).execute()

        shaped = []
        for row in (result.data or []):
            company_obj = row.pop("companies", None) or {}
            row["company_name"] = company_obj.get("name")
            shaped.append(row)

        return shaped
    except Exception:
        return []


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: str, user: CurrentUser = Depends(get_current_user)):
    my_company_ids = _get_my_company_ids(user.user_id)
    try:
        result = (
            supabase.table("issues")
            .select("id, company_id, title, amount, severity, status, source, created_at, companies(name)")
            .eq("id", issue_id)
            .in_("company_id", my_company_ids)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Issue not found.")

        row = result.data
        company_obj = row.pop("companies", None) or {}
        row["company_name"] = company_obj.get("name")
        return row
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found.")


@router.post("/{issue_id}/resolve", response_model=IssueOut)
def resolve_issue(
    issue_id: str,
    payload: IssueResolve = None,
    user: CurrentUser = Depends(get_current_user),
):
    my_company_ids = _get_my_company_ids(user.user_id)
    try:
        updates = {"status": IssueStatus.resolved.value}
        if payload and payload.resolution_note:
            updates["resolution_note"] = payload.resolution_note

        result = (
            supabase.table("issues")
            .update(updates)
            .eq("id", issue_id)
            .in_("company_id", my_company_ids)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Issue not found.")

        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
