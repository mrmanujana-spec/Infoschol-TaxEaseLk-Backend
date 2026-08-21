"""
Matches: Settings > Security tab
Sections on screen: Change Password, Two-Factor Authentication, Active Sessions

WHAT'S NOT HERE, ON PURPOSE:
- 2FA enroll/verify (the QR code + 6-digit code flow): this needs to run
  against the user's own Supabase session (specifically their refresh
  token), which our backend never receives -- only the short-lived access
  token comes through the Authorization header. Your frontend should call
  `supabase.auth.mfa.enroll()` / `.challengeAndVerify()` directly. What
  IS reliable from our backend is checking whether 2FA is currently on,
  and turning it off.
- A per-session list with device/location/last-active: your screenshot
  cuts off before showing those columns, and Supabase doesn't expose a
  "list sessions with device info" API. What IS reliable is signing the
  user out of every device at once ("revoke all sessions").
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role, CurrentUser
from app.database import supabase, supabase_anon
from app.schemas import ChangePasswordRequest, TwoFactorStatusOut, MessageOut

router = APIRouter(prefix="/auditor/security", tags=["Security"])


@router.post("/change-password", response_model=MessageOut)
def change_password(
    request: ChangePasswordRequest,
    user: CurrentUser = Depends(require_role("auditor")),
):
    # Step 1: prove they actually know the CURRENT password, by trying to
    # sign in as them with it (using the public anon key, same as a normal
    # login -- this does NOT create a session we keep, just checks it works)
    try:
        supabase_anon.auth.sign_in_with_password(
            {"email": user.email, "password": request.current_password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    # Step 2: now actually set the new password, via the admin API
    try:
        supabase.auth.admin.update_user_by_id(
            user.user_id, {"password": request.new_password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not update password: {e}")

    return {"message": "Password updated successfully."}


@router.get("/two-factor", response_model=TwoFactorStatusOut)
def get_two_factor_status(user: CurrentUser = Depends(require_role("auditor"))):
    result = supabase.auth.admin.get_user_by_id(user.user_id)
    factors = getattr(result.user, "factors", None) or []
    verified_factors = [f.id for f in factors if getattr(f, "status", None) == "verified"]
    return {"enabled": len(verified_factors) > 0, "factor_ids": verified_factors}


@router.post("/two-factor/disable", response_model=MessageOut)
def disable_two_factor(
    factor_id: str,
    user: CurrentUser = Depends(require_role("auditor")),
):
    """
    Turns off one enrolled 2FA factor. Requires the factor_id from
    GET /two-factor. (Enrolling a NEW factor must happen on the frontend --
    see the module docstring above for why.)
    """
    try:
        supabase.auth.admin.mfa.delete_factor({"id": factor_id, "user_id": user.user_id})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not disable 2FA: {e}")
    return {"message": "Two-factor authentication disabled."}


@router.post("/sessions/revoke-all", response_model=MessageOut)
def revoke_all_sessions(user: CurrentUser = Depends(require_role("auditor"))):
    """
    Signs the user out of every device/browser at once -- the one
    "Active Sessions" action we can do reliably without a custom
    sessions table. (See module docstring for why a per-device list
    isn't built here.)
    """
    try:
        supabase.auth.admin.sign_out(user.user_id, scope="global")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not revoke sessions: {e}")
    return {"message": "Signed out of all devices."}
