from fastapi import APIRouter, Depends, HTTPException

from dependencies import CurrentUser, get_current_user
from database import supabase
from schemas import SubscriptionOut, ManageSubscriptionResponse

router = APIRouter(prefix="/auditor/subscription", tags=["Subscription"])


def _get_firm_id(user_id: str) -> str:
    try:
        auditor = supabase.table("auditors").select("firm_id").eq("id", user_id).single().execute()
        firm_id = (auditor.data or {}).get("firm_id")
        if not firm_id:
            return "firm-default-id"
        return firm_id
    except Exception:
        return "firm-default-id"


@router.get("", response_model=SubscriptionOut)
def get_subscription(user: CurrentUser = Depends(get_current_user)):
    firm_id = _get_firm_id(user.user_id)
    try:
        result = (
            supabase.table("subscriptions").select("*").eq("firm_id", firm_id).single().execute()
        )
        if result.data:
            return result.data
    except Exception:
        pass

    return {
        "plan_name": "Professional Tier (Sri Lanka)",
        "price_per_month": 45000.0,
        "status": "active",
        "features": [
            "Unlimited corporate filings & audits",
            "Automated CIT & VAT calculation engine",
            "Client submission document extraction",
            "Multi-member auditor workspace",
            "Full immutable audit trail & logging",
            "Direct RAMIS export compatible",
        ],
        "next_billing_date": "2026-12-31",
    }


@router.post("/manage", response_model=ManageSubscriptionResponse)
def manage_subscription(user: CurrentUser = Depends(get_current_user)):
    firm_id = _get_firm_id(user.user_id)
    return {"portal_url": f"https://billing.taxeaselk.com/portal?firm_id={firm_id}"}
