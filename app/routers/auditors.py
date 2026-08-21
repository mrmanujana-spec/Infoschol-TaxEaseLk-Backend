"""
Matches: Settings > Profile tab
Fields on screen: Full Name, Email Address, Phone Number,
Professional License No., Organization, Designation, Change Photo

Assumes a Supabase table "auditors" with columns:
  id (uuid, = auth user id), full_name, email, phone, license_no,
  organization, designation, photo_url
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import AuditorProfileOut, AuditorProfileUpdate

router = APIRouter(prefix="/auditor", tags=["Auditor Profile"])


@router.get("/me", response_model=AuditorProfileOut)
def get_my_profile(user: CurrentUser = Depends(require_role("auditor"))):
    result = supabase.table("auditors").select("*").eq("id", user.user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Auditor profile not found.")
    return result.data


@router.put("/me", response_model=AuditorProfileOut)
def update_my_profile(
    updates: AuditorProfileUpdate,
    user: CurrentUser = Depends(require_role("auditor")),
):
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update.")
    result = supabase.table("auditors").update(payload).eq("id", user.user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Auditor profile not found.")
    return result.data[0]


@router.post("/me/photo", response_model=AuditorProfileOut)
def update_photo(
    photo_url: str,
    user: CurrentUser = Depends(require_role("auditor")),
):
    """
    NOTE: this endpoint just SAVES a photo URL. The actual image upload
    should go to Supabase Storage from your frontend first (or via a
    separate file-upload endpoint I can add), which gives you back a
    URL -- pass that URL here to attach it to the profile.
    """
    result = (
        supabase.table("auditors")
        .update({"photo_url": photo_url})
        .eq("id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Auditor profile not found.")
    return result.data[0]
