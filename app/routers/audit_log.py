"""
Matches: Audit Log screen
Filters: Company, User, Action, Date, Financial Year
Columns: Timestamp, Company, User, Action, Details

This table is written to by other routers (log_action in utils.py) --
there's no manual "create" endpoint here since it's meant to be an
immutable, automatic trail, exactly like the screen title says.
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import date

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import AuditLogOut

router = APIRouter(prefix="/auditor/audit-log", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogOut])
def get_audit_log(
    company_id: Optional[str] = None,
    user_name: Optional[str] = Query(None, description="Filter by who performed the action"),
    action: Optional[str] = None,
    on_date: Optional[date] = None,
    financial_year: Optional[str] = None,
    user: CurrentUser = Depends(require_role("auditor")),
):
    company_ids_query = supabase.table("companies").select("id").eq(
        "assigned_auditor_id", user.user_id
    )
    if financial_year:
        company_ids_query = company_ids_query.eq("financial_year", financial_year)
    company_ids = [c["id"] for c in company_ids_query.execute().data]

    if not company_ids:
        return []

    query = (
        supabase.table("audit_log")
        .select("*, companies(name)")
        .in_("company_id", company_ids)
    )
    if company_id:
        query = query.eq("company_id", company_id)
    if user_name:
        query = query.ilike("user_name", f"%{user_name}%")
    if action:
        query = query.ilike("action", f"%{action}%")
    if on_date:
        query = query.gte("created_at", f"{on_date}T00:00:00").lte(
            "created_at", f"{on_date}T23:59:59"
        )

    result = query.order("created_at", desc=True).execute()

    rows = []
    for row in result.data:
        company = row.pop("companies", None) or {}
        row["company_name"] = company.get("name")
        rows.append(row)
    return rows
