"""
Matches: Issues screen
Summary cards: Critical, Warnings, Information, Resolved (counts)
Tabs: All, Critical, Warnings, Information, Resolved
Columns: Issue, Company, Amount, Severity, Status, Source, Action (Review/Resolve)

Assumes a Supabase table "issues" with columns:
  id (uuid), company_id (uuid), title, amount (numeric), severity,
  status, source, created_at, resolved_at
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import IssueOut, IssueResolve, IssueSummaryOut, IssueSeverity, IssueStatus
from app.utils import log_action

router = APIRouter(prefix="/auditor/issues", tags=["Issues"])


def _company_ids_for_auditor(user_id: str) -> List[str]:
    companies = (
        supabase.table("companies").select("id").eq("assigned_auditor_id", user_id).execute()
    )
    return [c["id"] for c in companies.data]


@router.get("/summary", response_model=IssueSummaryOut)
def get_issue_summary(user: CurrentUser = Depends(require_role("auditor"))):
    company_ids = _company_ids_for_auditor(user.user_id)
    if not company_ids:
        return {"critical": 0, "warnings": 0, "information": 0, "resolved": 0}

    all_issues = supabase.table("issues").select("severity, status").in_(
        "company_id", company_ids
    ).execute().data

    return {
        "critical": sum(1 for i in all_issues if i["severity"] == "critical" and i["status"] == "open"),
        "warnings": sum(1 for i in all_issues if i["severity"] == "warning" and i["status"] == "open"),
        "information": sum(1 for i in all_issues if i["severity"] == "info" and i["status"] == "open"),
        "resolved": sum(1 for i in all_issues if i["status"] == "resolved"),
    }


@router.get("", response_model=List[IssueOut])
def list_issues(
    severity: Optional[IssueSeverity] = None,
    status: Optional[IssueStatus] = None,
    company_id: Optional[str] = None,
    user: CurrentUser = Depends(require_role("auditor")),
):
    company_ids = _company_ids_for_auditor(user.user_id)
    if not company_ids:
        return []

    query = supabase.table("issues").select("*, companies(name)").in_("company_id", company_ids)
    if severity:
        query = query.eq("severity", severity.value)
    if status:
        query = query.eq("status", status.value)
    if company_id:
        query = query.eq("company_id", company_id)

    result = query.order("created_at", desc=True).execute()

    # flatten the joined company name onto each issue
    issues = []
    for row in result.data:
        company = row.pop("companies", None) or {}
        row["company_name"] = company.get("name")
        issues.append(row)
    return issues


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: str, user: CurrentUser = Depends(require_role("auditor"))):
    company_ids = _company_ids_for_auditor(user.user_id)
    result = (
        supabase.table("issues")
        .select("*, companies(name)")
        .eq("id", issue_id)
        .in_("company_id", company_ids)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Issue not found.")

    row = result.data
    company = row.pop("companies", None) or {}
    row["company_name"] = company.get("name")
    return row


@router.post("/{issue_id}/resolve", response_model=IssueOut)
def resolve_issue(
    issue_id: str,
    resolution: IssueResolve,
    user: CurrentUser = Depends(require_role("auditor")),
):
    company_ids = _company_ids_for_auditor(user.user_id)
    existing = (
        supabase.table("issues")
        .select("*")
        .eq("id", issue_id)
        .in_("company_id", company_ids)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Issue not found.")

    result = (
        supabase.table("issues")
        .update({"status": "resolved"})
        .eq("id", issue_id)
        .execute()
    )
    updated = result.data[0]

    # keep the company's critical/warning counters in sync
    company_id = updated["company_id"]
    severity = existing.data["severity"]
    if severity in ("critical", "warning"):
        counter_field = "critical_issues_count" if severity == "critical" else "warnings_count"
        company = (
            supabase.table("companies").select(counter_field).eq("id", company_id).single().execute()
        )
        current_count = (company.data or {}).get(counter_field, 0) or 0
        supabase.table("companies").update(
            {counter_field: max(current_count - 1, 0)}
        ).eq("id", company_id).execute()

    log_action(
        company_id=company_id,
        user_type="Auditor",
        user_name=user.email,
        action="Issue Reviewed",
        details=resolution.resolution_note or f"Resolved: {existing.data['title']}",
    )

    company = supabase.table("companies").select("name").eq("id", company_id).single().execute()
    updated["company_name"] = company.data.get("name") if company.data else None
    return updated
