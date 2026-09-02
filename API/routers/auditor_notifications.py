from fastapi import APIRouter, Depends, HTTPException

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import NotificationPreferencesOut, NotificationPreferencesUpdate

router = APIRouter(prefix="/auditor/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationPreferencesOut)
def get_notification_preferences(user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("notification_preferences")
            .select("*")
            .eq("auditor_id", user.user_id)
            .execute()
        )
        if result.data:
            return result.data[0]

        default_prefs = {
            "auditor_id": user.user_id,
            "new_submissions": True,
            "business_responses": True,
            "document_uploads": True,
            "messages": True,
            "review_reminders": True,
        }
        created = supabase.table("notification_preferences").insert(default_prefs).execute()
        return created.data[0] if created.data else default_prefs
    except Exception:
        return {
            "new_submissions": True,
            "business_responses": True,
            "document_uploads": True,
            "messages": True,
            "review_reminders": True,
        }


@router.put("", response_model=NotificationPreferencesOut)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    try:
        result = (
            supabase.table("notification_preferences")
            .update(updates)
            .eq("auditor_id", user.user_id)
            .execute()
        )
        if not result.data:
            updates["auditor_id"] = user.user_id
            result = supabase.table("notification_preferences").insert(updates).execute()

        return result.data[0] if result.data else updates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not update preferences: {e}")
