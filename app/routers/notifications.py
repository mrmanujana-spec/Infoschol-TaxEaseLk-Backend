"""
Matches: Settings > Notifications tab
5 toggles on screen: New submissions, Business responses,
Document uploads, Messages, Review reminders

Assumes a Supabase table "notification_preferences" with columns:
  auditor_id (uuid, primary key, references auditors(id)),
  new_submissions (bool, default true), business_responses (bool, default true),
  document_uploads (bool, default false), messages (bool, default true),
  review_reminders (bool, default true)

One row per auditor, created the first time they're fetched if missing.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import NotificationPreferencesOut, NotificationPreferencesUpdate

router = APIRouter(prefix="/auditor/notifications", tags=["Notifications"])

DEFAULTS = {
    "new_submissions": True,
    "business_responses": True,
    "document_uploads": False,
    "messages": True,
    "review_reminders": True,
}


@router.get("", response_model=NotificationPreferencesOut)
def get_notification_preferences(user: CurrentUser = Depends(require_role("auditor"))):
    result = (
        supabase.table("notification_preferences")
        .select("*")
        .eq("auditor_id", user.user_id)
        .maybe_single()
        .execute()
    )
    if result.data:
        return result.data

    # first time this auditor's preferences are requested -- create the
    # row with the same defaults shown on screen (matches the toggle
    # states in your screenshot: only "Document uploads" starts off)
    payload = {"auditor_id": user.user_id, **DEFAULTS}
    created = supabase.table("notification_preferences").insert(payload).execute()
    return created.data[0]


@router.put("", response_model=NotificationPreferencesOut)
def update_notification_preferences(
    updates: NotificationPreferencesUpdate,
    user: CurrentUser = Depends(require_role("auditor")),
):
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = (
        supabase.table("notification_preferences")
        .update(payload)
        .eq("auditor_id", user.user_id)
        .execute()
    )
    if not result.data:
        # row doesn't exist yet -- create it with defaults + these overrides
        row = {"auditor_id": user.user_id, **DEFAULTS, **payload}
        result = supabase.table("notification_preferences").insert(row).execute()
    return result.data[0]
