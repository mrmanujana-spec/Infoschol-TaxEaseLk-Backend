from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import AuditLogOut, AuditUserType

router = APIRouter(prefix="/auditor/audit-log", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogOut])
def get_audit_log(
    company_id: Optional[str] = None,
    user_type: Optional[AuditUserType] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        my_companies = (
            supabase.table("companies")
            .select("id")
            .eq("assigned_auditor_id", user.user_id)
            .execute()
        )
        my_company_ids = [c["id"] for c in (my_companies.data or [])]
    except Exception:
        my_company_ids = []

    if not my_company_ids and not company_id:
        return []

    try:
        query = (
            supabase.table("audit_log")
            .select("id, company_id, user_type, user_name, action, details, created_at, companies(name)")
        )

        if company_id:
            query = query.eq("company_id", company_id)
        else:
            query = query.in_("company_id", my_company_ids)

        if user_type:
            query = query.eq("user_type", user_type.value)
        if date_from:
            query = query.gte("created_at", f"{date_from}T00:00:00")
        if date_to:
            query = query.lte("created_at", f"{date_to}T23:59:59")

        result = query.order("created_at", desc=True).execute()

        shaped = []
        for row in (result.data or []):
            company_obj = row.pop("companies", None) or {}
            row["company_name"] = company_obj.get("name")
            shaped.append(row)

        return shaped
    except Exception as e:
        print(f"Audit log query error: {e}")
        return []
