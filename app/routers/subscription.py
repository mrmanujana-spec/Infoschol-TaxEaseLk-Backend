"""
Matches: Settings > Subscription tab
Shows: plan name, price/month, Active badge, feature list, next billing
date, "Manage Subscription" button.

Assumes a Supabase table "subscriptions" with columns:
  id (uuid), firm_id (uuid, references firms(id)), plan_name,
  price_per_month (numeric), status, features (jsonb array of text),
  next_billing_date (date)

NOTE on "Manage Subscription": that button almost always hands off to
your payment provider's own hosted billing page (e.g. Stripe Customer
Portal). I don't know which gateway you're using, so this endpoint is
a stub that returns a placeholder URL -- tell me your payment provider
(Stripe, PayHere, etc.) and I'll wire it to actually create a real
portal session.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role, CurrentUser
from app.database import supabase
from app.schemas import SubscriptionOut, ManageSubscriptionResponse

router = APIRouter(prefix="/auditor/subscription", tags=["Subscription"])


def _get_firm_id(user_id: str) -> str:
    auditor = supabase.table("auditors").select("firm_id").eq("id", user_id).single().execute()
    firm_id = (auditor.data or {}).get("firm_id")
    if not firm_id:
        raise HTTPException(status_code=404, detail="No firm linked to this auditor yet.")
    return firm_id


@router.get("", response_model=SubscriptionOut)
def get_subscription(user: CurrentUser = Depends(require_role("auditor"))):
    firm_id = _get_firm_id(user.user_id)
    result = (
        supabase.table("subscriptions").select("*").eq("firm_id", firm_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No subscription found for this firm.")
    return result.data


@router.post("/manage", response_model=ManageSubscriptionResponse)
def manage_subscription(user: CurrentUser = Depends(require_role("auditor"))):
    """
    STUB: real version should call your payment provider's API to create
    a billing portal session and return that URL. Placeholder for now.
    """
    firm_id = _get_firm_id(user.user_id)
    return {"portal_url": f"https://billing.example.com/portal?firm_id={firm_id}"}
