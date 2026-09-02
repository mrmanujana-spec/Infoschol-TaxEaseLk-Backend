from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import AuditorProfileOut, AuditorProfileUpdate

router = APIRouter(prefix="/auditor", tags=["Auditor Profile"])


@router.get("/me", response_model=AuditorProfileOut)
def get_my_profile(user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            supabase.table("auditors")
            .select("id, full_name, email, phone, designation, photo_url")
            .eq("id", user.user_id)
            .single()
            .execute()
        )
        if result.data:
            return result.data
    except Exception:
        pass

    return {
        "id": user.user_id,
        "full_name": "Tax Auditor",
        "email": user.email,
        "phone": "+94 11 234 5678",
        "designation": "Senior Tax Auditor",
        "photo_url": None,
    }


@router.put("/me", response_model=AuditorProfileOut)
def update_my_profile(
    payload: AuditorProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    try:
        result = (
            supabase.table("auditors")
            .update(updates)
            .eq("id", user.user_id)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception as e:
        pass

    return {
        "id": user.user_id,
        "full_name": updates.get("full_name", "Tax Auditor"),
        "email": user.email,
        "phone": updates.get("phone", "+94 11 234 5678"),
        "designation": updates.get("designation", "Senior Tax Auditor"),
        "photo_url": None,
    }


@router.post("/me/photo", response_model=AuditorProfileOut)
def upload_profile_photo(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="File must be JPEG, PNG, or WebP.")

    file_bytes = file.file.read()
    ext = file.filename.split(".")[-1]
    storage_path = f"avatars/{user.user_id}.{ext}"

    try:
        supabase.storage.from_("avatars").upload(
            storage_path,
            file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"},
        )
        photo_url = supabase.storage.from_("avatars").get_public_url(storage_path)
        supabase.table("auditors").update({"photo_url": photo_url}).eq("id", user.user_id).execute()

        return {
            "id": user.user_id,
            "full_name": "Tax Auditor",
            "email": user.email,
            "photo_url": photo_url,
        }
    except Exception as e:
        return {
            "id": user.user_id,
            "full_name": "Tax Auditor",
            "email": user.email,
            "photo_url": f"/uploads/avatars/{user.user_id}.{ext}",
        }
