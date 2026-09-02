from fastapi import APIRouter, Depends
from typing import List

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import (
    DashboardSummaryOut,
    WorkloadOut,
    PriorityReviewOut,
    AuditLogOut,
    CompanyOut,
    ReviewStatus,
)

router = APIRouter(prefix="/auditor/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def get_summary_metrics(user: CurrentUser = Depends(get_current_user)):
    try:
        companies = (
            supabase.table("companies")
            .select("id, review_status, critical_issues_count")
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        data = companies.data or []
        total = len(data)
        pending = sum(
            1 for c in data if c.get("review_status") not in (ReviewStatus.completed.value, ReviewStatus.not_started.value)
        )
        critical = sum(c.get("critical_issues_count", 0) for c in data)
        completed = sum(1 for c in data if c.get("review_status") == ReviewStatus.completed.value)

        return {
            "companies_assigned": total,
            "pending_reviews": pending,
            "critical_issues": critical,
            "completed": completed,
        }
    except Exception:
        return {
            "companies_assigned": 0,
            "pending_reviews": 0,
            "critical_issues": 0,
            "completed": 0,
        }


@router.get("/workload", response_model=WorkloadOut)
def get_workload_breakdown(user: CurrentUser = Depends(get_current_user)):
    try:
        companies = (
            supabase.table("companies")
            .select("review_status")
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        data = companies.data or []
        counts = {s.value: 0 for s in ReviewStatus}
        for c in data:
            status = c.get("review_status")
            if status in counts:
                counts[status] += 1

        return {
            "pending": counts[ReviewStatus.pending.value],
            "in_progress": counts[ReviewStatus.in_progress.value],
            "waiting_for_company": counts[ReviewStatus.waiting_for_company.value],
            "ready_for_approval": counts[ReviewStatus.ready_for_approval.value],
            "completed": counts[ReviewStatus.completed.value],
        }
    except Exception:
        return {
            "pending": 0,
            "in_progress": 0,
            "waiting_for_company": 0,
            "ready_for_approval": 0,
            "completed": 0,
        }


@router.get("/priority-reviews", response_model=List[PriorityReviewOut])
def get_priority_reviews(user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("companies")
            .select("id, name, risk_level, critical_issues_count, warnings_count, due_date, progress_percent")
            .eq("assigned_auditor_id", user.user_id)
            .neq("review_status", ReviewStatus.completed.value)
            .order("critical_issues_count", desc=True)
            .order("due_date")
            .limit(5)
            .execute()
        )

        shaped = []
        for c in (result.data or []):
            risk = c.get("risk_level")
            crit = c.get("critical_issues_count", 0)
            if crit > 0 or risk == "high":
                label = "High Risk"
            elif c.get("warnings_count", 0) > 0 or risk == "medium":
                label = "Medium Risk"
            else:
                label = "Normal"

            shaped.append(
                {
                    "company_id": c["id"],
                    "company_name": c["name"],
                    "priority_label": label,
                    "critical_issues_count": crit,
                    "warnings_count": c.get("warnings_count", 0),
                    "due_date": c.get("due_date"),
                    "progress_percent": c.get("progress_percent", 0),
                }
            )
        return shaped
    except Exception:
        return []


@router.get("/recent-activity", response_model=List[AuditLogOut])
def get_recent_activity(user: CurrentUser = Depends(get_current_user)):
    try:
        my_companies = (
            supabase.table("companies")
            .select("id")
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        my_company_ids = [c["id"] for c in (my_companies.data or [])]
        if not my_company_ids:
            return []

        result = (
            supabase.table("audit_log")
            .select("id, company_id, user_type, user_name, action, details, created_at, companies(name)")
            .in_("company_id", my_company_ids)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        shaped = []
        for row in (result.data or []):
            company_obj = row.pop("companies", None) or {}
            row["company_name"] = company_obj.get("name")
            shaped.append(row)
        return shaped
    except Exception:
        return []


@router.get("/upcoming-deadlines", response_model=List[CompanyOut])
def get_upcoming_deadlines(user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("companies")
            .select("*")
            .eq("assigned_auditor_id", user.user_id)
            .neq("review_status", ReviewStatus.completed.value)
            .not_.is_("due_date", "null")
            .order("due_date")
            .limit(5)
            .execute()
        )
        return result.data or []
    except Exception:
        return []
