"""
TaxEaseLK — Unified Dependencies
"""

from typing import Optional
from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import Business, get_db


@dataclass
class CurrentUser:
    user_id: str
    email: str


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
) -> CurrentUser:
    """Return the current auditor or authenticated user from request headers."""
    if not x_user_id or not x_user_email:
        # Fallback to demo/default user if header not present in development
        return CurrentUser(user_id="auditor-default-id", email="auditor@taxeaselk.com")
    return CurrentUser(user_id=x_user_id, email=x_user_email)


def get_current_business(
    x_business_id: Optional[str] = Header(None, alias="X-Business-Id"),
    x_business_email: Optional[str] = Header(None, alias="X-Business-Email"),
    db: Session = Depends(get_db),
) -> Business:
    """Return the active business without requiring a complex auth layer."""

    business_id: Optional[int] = None
    business_email: Optional[str] = None

    if x_business_id:
        try:
            business_id = int(x_business_id)
        except ValueError:
            business_id = None

    if x_business_email:
        business_email = x_business_email.strip().lower()

    if business_id is not None:
        business = db.query(Business).filter(Business.id == business_id).first()
    elif business_email:
        business = db.query(Business).filter(Business.email == business_email).first()
    else:
        business = db.query(Business).filter(Business.is_active == True).order_by(Business.id.asc()).first()

    if business is None:
        # If no business exists yet in database, create a default demo business
        try:
            business = Business(
                company_name="Apex Holdings (Pvt) Ltd",
                email="admin@apexholdings.lk",
                registration_number="PV123456",
                tin="100234567-0000",
                phone="+94 11 234 5678",
                address="No. 45, Galle Road, Colombo 03, Sri Lanka",
                industry="Information Technology",
                is_active=True
            )
            db.add(business)
            db.commit()
            db.refresh(business)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No active business found. Provide X-Business-Id or X-Business-Email.",
            )

    return business
