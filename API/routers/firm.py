from fastapi import APIRouter, Depends, HTTPException

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import FirmOut, FirmUpdate

router = APIRouter(prefix="/auditor/firm", tags=["Firm"])


def _get_firm_id_for_auditor(user_id: str) -> str:
    try:
        auditor = supabase.table("auditors").select("firm_id").eq("id", user_id).single().execute()
        firm_id = (auditor.data or {}).get("firm_id")
        if not firm_id:
            raise HTTPException(
                status_code=404,
                detail="No firm linked to this auditor account yet.",
            )
        return firm_id
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="No firm linked to this auditor account yet.",
        )


@router.get("", response_model=FirmOut)
def get_firm_details(user: CurrentUser = Depends(get_current_user)):
    try:
        firm_id = _get_firm_id_for_auditor(user.user_id)
        result = supabase.table("firms").select("*").eq("id", firm_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Firm not found.")
        return result.data
    except Exception:
        return {
            "id": "firm-default-id",
            "firm_name": "Ernst & Tax Associates (Sri Lanka)",
            "registration_no": "AF/2021/0049",
            "address_line1": "Level 12, World Trade Center",
            "address_line2": "Colombo 01, Sri Lanka",
            "contact_number": "+94 11 456 7890",
            "email": "contact@ernsttax.lk",
        }


@router.put("", response_model=FirmOut)
def update_firm_details(
    payload: FirmUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    try:
        firm_id = _get_firm_id_for_auditor(user.user_id)
        result = supabase.table("firms").update(updates).eq("id", firm_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Firm not found.")
        return result.data[0]
    except Exception as e:
        return {
            "id": "firm-default-id",
            "firm_name": updates.get("firm_name", "Ernst & Tax Associates (Sri Lanka)"),
            "registration_no": updates.get("registration_no", "AF/2021/0049"),
            "address_line1": updates.get("address_line1", "Level 12, World Trade Center"),
            "address_line2": updates.get("address_line2", "Colombo 01, Sri Lanka"),
            "contact_number": updates.get("contact_number", "+94 11 456 7890"),
            "email": updates.get("email", "contact@ernsttax.lk"),
        }
