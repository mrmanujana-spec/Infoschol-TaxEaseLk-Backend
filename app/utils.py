"""
Every meaningful action (approve, resolve, request info) needs to show
up in the Audit Log screen. Rather than repeat the insert code in every
router, every action calls this one function.
"""

from app.database import supabase


def log_action(
    company_id: str,
    user_type: str,
    action: str,
    user_name: str | None = None,
    details: str | None = None,
) -> None:
    supabase.table("audit_log").insert(
        {
            "company_id": company_id,
            "user_type": user_type,
            "user_name": user_name,
            "action": action,
            "details": details,
        }
    ).execute()
