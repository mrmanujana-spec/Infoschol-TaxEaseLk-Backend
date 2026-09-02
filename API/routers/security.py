from fastapi import APIRouter, Depends, HTTPException

from dependencies import CurrentUser, get_current_user
from database import supabase, supabase_anon
from schemas import ChangePasswordRequest, TwoFactorStatusOut, MessageOut

router = APIRouter(prefix="/auditor/security", tags=["Security"])


@router.post("/change-password", response_model=MessageOut)
def change_password(
    request: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
):
    # Step 1: verify current password using anon client
    try:
        supabase_anon.auth.sign_in_with_password(
            {"email": user.email, "password": request.current_password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    # Step 2: update password via admin API
    try:
        supabase.auth.admin.update_user_by_id(
            user.user_id, {"password": request.new_password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not update password: {e}")

    return {"message": "Password updated successfully."}


@router.get("/two-factor", response_model=TwoFactorStatusOut)
def get_two_factor_status(user: CurrentUser = Depends(get_current_user)):
    try:
        result = supabase.auth.admin.get_user_by_id(user.user_id)
        factors = getattr(result.user, "factors", None) or []
        verified_factors = [f.id for f in factors if getattr(f, "status", None) == "verified"]
        return {"enabled": len(verified_factors) > 0, "factor_ids": verified_factors}
    except Exception:
        return {"enabled": False, "factor_ids": []}


@router.post("/two-factor/disable", response_model=MessageOut)
def disable_two_factor(
    factor_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        supabase.auth.admin.mfa.delete_factor({"id": factor_id, "user_id": user.user_id})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not disable 2FA: {e}")
    return {"message": "Two-factor authentication disabled."}


@router.post("/sessions/revoke-all", response_model=MessageOut)
def revoke_all_sessions(user: CurrentUser = Depends(get_current_user)):
    try:
        supabase.auth.admin.sign_out(user.user_id, scope="global")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not revoke sessions: {e}")
    return {"message": "Signed out of all devices."}
