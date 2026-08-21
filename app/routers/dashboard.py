"""
Matches: Dashboard screen
- 4 summary cards: Companies Assigned, Pending Reviews, Critical Issues, Completed
- Priority Reviews list (cards with Review/Approve buttons)
- My Review Workload (counts per stage)
- Recent Activity (latest audit log entries)
- Upcoming Deadlines
"""

from fastapi import APIRouter, Depends, Query
from typing import List

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import DashboardSummaryOut, WorkloadOut, PriorityReviewOut, AuditLogOut, CompanyOut

router = APIRouter(prefix="/auditor/dashboard", tags=["Dashboard"])


def _companies_for_auditor(user_id: str):
    return supabase.table("companies").select("*").eq("assigned_auditor_id", user_id).execute().data


@router.get("/summary", response_model=DashboardSummaryOut)
def get_summary(user: CurrentUser = Depends(require_role("auditor"))):
    companies = _companies_for_auditor(user.user_id)
    return {
        "companies_assigned": len(companies),
        "pending_reviews": sum(
            1 for c in companies if c["review_status"] in ("pending", "in_progress", "waiting_for_company")
        ),
        "critical_issues": sum(c.get("critical_issues_count", 0) for c in companies),
        "completed": sum(1 for c in companies if c["review_status"] == "completed"),
    }


@router.get("/workload", response_model=WorkloadOut)
def get_workload(user: CurrentUser = Depends(require_role("auditor"))):
    companies = _companies_for_auditor(user.user_id)
    counts = {
        "pending": 0,
        "in_progress": 0,
        "waiting_for_company": 0,
        "ready_for_approval": 0,
        "completed": 0,
    }
    for c in companies:
        status = c["review_status"]
        if status in counts:
            counts[status] += 1
    return counts


@router.get("/priority-reviews", response_model=List[PriorityReviewOut])
def get_priority_reviews(
    limit: int = Query(5, ge=1, le=20),
    user: CurrentUser = Depends(require_role("auditor")),
):
    companies = _companies_for_auditor(user.user_id)

    reviews = []
    for c in companies:
        if c.get("critical_issues_count", 0) > 0:
            label = "CRITICAL"
        elif c["review_status"] == "waiting_for_company" or c.get("warnings_count", 0) > 0:
            label = "ATTENTION_REQUIRED"
        elif c["review_status"] == "ready_for_approval":
            label = "READY_FOR_APPROVAL"
        else:
            continue  # not a priority item

        reviews.append(
            {
                "company_id": c["id"],
                "company_name": c["name"],
                "priority_label": label,
                "critical_issues_count": c.get("critical_issues_count", 0),
                "warnings_count": c.get("warnings_count", 0),
                "due_date": c.get("due_date"),
                "progress_percent": c.get("progress_percent", 0),
            }
        )

    # Critical first, then attention required, then ready for approval
    order = {"CRITICAL": 0, "ATTENTION_REQUIRED": 1, "READY_FOR_APPROVAL": 2}
    reviews.sort(key=lambda r: order[r["priority_label"]])
    return reviews[:limit]


@router.get("/recent-activity", response_model=List[AuditLogOut])
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    user: CurrentUser = Depends(require_role("auditor")),
):
    company_ids = [c["id"] for c in _companies_for_auditor(user.user_id)]
    if not company_ids:
        return []

    result = (
        supabase.table("audit_log")
        .select("*, companies(name)")
        .in_("company_id", company_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = []
    for row in result.data:
        company = row.pop("companies", None) or {}
        row["company_name"] = company.get("name")
        rows.append(row)
    return rows


@router.get("/upcoming-deadlines", response_model=List[CompanyOut])
def get_upcoming_deadlines(
    days: int = Query(14, ge=1, le=90),
    user: CurrentUser = Depends(require_role("auditor")),
):
    from datetime import date, timedelta

    today = date.today()
    cutoff = today + timedelta(days=days)

    result = (
        supabase.table("companies")
        .select("*")
        .eq("assigned_auditor_id", user.user_id)
        .neq("review_status", "completed")
        .gte("due_date", today.isoformat())
        .lte("due_date", cutoff.isoformat())
        .order("due_date")
        .execute()
    )
    return result.data
