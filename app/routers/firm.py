"""
Matches: Settings > Firm tab
Fields on screen: Firm Name, Registration No., Address Line 1,
Address Line 2, Contact Number, Email

Assumes a Supabase table "firms" with columns:
  id (uuid), firm_name, registration_no, address_line1, address_line2,
  contact_number, email

And that "auditors" has a firm_id column referencing firms(id) --
add this column to the auditors table from the earlier README SQL:
  alter table auditors add column firm_id uuid references firms(id);
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import FirmOut, FirmUpdate

router = APIRouter(prefix="/auditor/firm", tags=["Firm"])


def _get_firm_id(user_id: str) -> str:
    auditor = supabase.table("auditors").select("firm_id").eq("id", user_id).single().execute()
    firm_id = (auditor.data or {}).get("firm_id")
    if not firm_id:
        raise HTTPException(status_code=404, detail="No firm linked to this auditor yet.")
    return firm_id


@router.get("", response_model=FirmOut)
def get_my_firm(user: CurrentUser = Depends(require_role("auditor"))):
    firm_id = _get_firm_id(user.user_id)
    result = supabase.table("firms").select("*").eq("id", firm_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Firm not found.")
    return result.data


@router.put("", response_model=FirmOut)
def update_my_firm(
    updates: FirmUpdate,
    user: CurrentUser = Depends(require_role("auditor")),
):
    firm_id = _get_firm_id(user.user_id)
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = supabase.table("firms").update(payload).eq("id", firm_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Firm not found.")
    return result.data[0]
