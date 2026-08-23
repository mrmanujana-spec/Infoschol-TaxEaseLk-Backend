import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import json, random, string

from database import (
    get_db, Business, FinancialYear, CompanyUser, SecuritySetting,
    UserSession, NotificationPreference, AuditLog,
    UserRoleEnum, UserStatusEnum
)
from auth import get_current_business

router = APIRouter(prefix="/settings", tags=["Settings"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CompanyUpdate(BaseModel):
    company_name:        Optional[str] = None
    registration_number: Optional[str] = None
    tin:                 Optional[str] = None
    phone:               Optional[str] = None
    address:             Optional[str] = None
    industry:            Optional[str] = None
    incorporation_date:  Optional[datetime] = None

class FinancialYearCreate(BaseModel):
    year_label:  str
    start_date:  datetime
    end_date:    datetime
    is_current:  Optional[bool] = False

class FinancialYearUpdate(BaseModel):
    year_label:        Optional[str]      = None
    start_date:        Optional[datetime] = None
    end_date:          Optional[datetime] = None
    accounting_profit: Optional[float]    = None
    taxable_income:    Optional[float]    = None
    estimated_cit:     Optional[float]    = None
    is_current:        Optional[bool]     = None
    is_filed:          Optional[bool]     = None

class UserInviteRequest(BaseModel):
    name:  str
    email: str
    role:  UserRoleEnum = UserRoleEnum.viewer

class UserUpdate(BaseModel):
    name:  Optional[str]          = None
    role:  Optional[UserRoleEnum] = None
    permissions: Optional[str]   = None

class UserStatusUpdate(BaseModel):
    status: UserStatusEnum

class SecurityUpdate(BaseModel):
    session_timeout_mins: Optional[int]  = None
    login_notifications:  Optional[bool] = None
    ip_whitelist:         Optional[str]  = None

class TwoFAVerify(BaseModel):
    code: str

class NotificationPrefUpdate(BaseModel):
    email_notifications: Optional[bool] = None
    sms_notifications:   Optional[bool] = None
    filing_deadlines:    Optional[bool] = None
    document_processed:  Optional[bool] = None
    auditor_updates:     Optional[bool] = None
    system_alerts:       Optional[bool] = None
    weekly_summary:      Optional[bool] = None


# ─── Audit log helper ─────────────────────────────────────────────────────────

def log_action(db, business_id, user_email, action, resource=None, resource_id=None, details=None):
    log = AuditLog(
        business_id = business_id,
        user_email  = user_email,
        action      = action,
        resource    = resource,
        resource_id = resource_id,
        details     = details,
        created_at  = datetime.utcnow(),
    )
    db.add(log)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# COMPANY SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/company")
def get_company(
    current_business: Business = Depends(get_current_business),
):
    """Get company information."""
    return {
        "id":                  current_business.id,
        "company_name":        current_business.company_name,
        "email":               current_business.email,
        "registration_number": current_business.registration_number,
        "tin":                 current_business.tin,
        "phone":               current_business.phone,
        "address":             current_business.address,
        "industry":            current_business.industry,
        "incorporation_date":  current_business.incorporation_date,
        "auditor_status":      current_business.auditor_status,
        "created_at":          current_business.created_at,
        "updated_at":          current_business.updated_at,
    }


@router.put("/company")
def update_company(
    payload:          CompanyUpdate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Update company information."""
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current_business, field, value)
    current_business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_business)

    log_action(db, current_business.id, current_business.email,
               "company_updated", "business", current_business.id)

    return {"message": "Company updated successfully.", "company_name": current_business.company_name}


# ══════════════════════════════════════════════════════════════════════════════
# FINANCIAL YEARS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/financial-years")
def get_financial_years(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get all available financial years."""
    years = db.query(FinancialYear).filter(
        FinancialYear.business_id == current_business.id
    ).order_by(FinancialYear.start_date.desc()).all()

    return {
        "total": len(years),
        "financial_years": [
            {
                "id":                fy.id,
                "year_label":        fy.year_label,
                "start_date":        fy.start_date,
                "end_date":          fy.end_date,
                "accounting_profit": fy.accounting_profit,
                "taxable_income":    fy.taxable_income,
                "estimated_cit":     fy.estimated_cit,
                "is_current":        fy.is_current,
                "is_filed":          fy.is_filed,
                "created_at":        fy.created_at,
            }
            for fy in years
        ],
    }


@router.post("/financial-years", status_code=201)
def create_financial_year(
    payload:          FinancialYearCreate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Create a new financial year."""
    # If new year is current, unset others
    if payload.is_current:
        db.query(FinancialYear).filter(
            FinancialYear.business_id == current_business.id
        ).update({"is_current": False})

    fy = FinancialYear(
        business_id = current_business.id,
        year_label  = payload.year_label,
        start_date  = payload.start_date,
        end_date    = payload.end_date,
        is_current  = payload.is_current or False,
    )
    db.add(fy)
    db.commit()
    db.refresh(fy)

    log_action(db, current_business.id, current_business.email,
               "financial_year_created", "financial_year", fy.id, fy.year_label)

    return {"message": "Financial year created.", "id": fy.id, "year_label": fy.year_label}


@router.patch("/financial-years/{financial_year_id}")
def update_financial_year(
    financial_year_id: int,
    payload:           FinancialYearUpdate,
    current_business:  Business = Depends(get_current_business),
    db:                Session  = Depends(get_db),
):
    """Update a financial year."""
    fy = db.query(FinancialYear).filter(
        FinancialYear.id          == financial_year_id,
        FinancialYear.business_id == current_business.id,
    ).first()
    if not fy:
        raise HTTPException(status_code=404, detail="Financial year not found.")

    if payload.is_current:
        db.query(FinancialYear).filter(
            FinancialYear.business_id == current_business.id,
            FinancialYear.id          != financial_year_id,
        ).update({"is_current": False})

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(fy, field, value)
    db.commit()

    log_action(db, current_business.id, current_business.email,
               "financial_year_updated", "financial_year", fy.id)

    return {"message": "Financial year updated.", "id": fy.id, "year_label": fy.year_label}


# ══════════════════════════════════════════════════════════════════════════════
# USERS AND ACCESS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/users")
def get_users(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get all company users."""
    users = db.query(CompanyUser).filter(
        CompanyUser.business_id == current_business.id
    ).order_by(CompanyUser.created_at.desc()).all()

    return {
        "total": len(users),
        "users": [
            {
                "id":         u.id,
                "name":       u.name,
                "email":      u.email,
                "role":       u.role,
                "status":     u.status,
                "permissions":u.permissions,
                "invited_at": u.invited_at,
                "joined_at":  u.joined_at,
            }
            for u in users
        ],
    }


@router.post("/users/invite", status_code=201)
def invite_user(
    payload:          UserInviteRequest,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Invite a new user or auditor to the company."""
    existing = db.query(CompanyUser).filter(
        CompanyUser.business_id == current_business.id,
        CompanyUser.email       == payload.email,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"{payload.email} is already a user.")

    user = CompanyUser(
        business_id = current_business.id,
        name        = payload.name,
        email       = payload.email,
        role        = payload.role,
        status      = UserStatusEnum.invited,
        invited_at  = datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, current_business.id, current_business.email,
               "user_invited", "company_user", user.id, payload.email)

    return {
        "message": f"Invitation sent to {payload.email}.",
        "id":      user.id,
        "email":   user.email,
        "role":    user.role,
        "status":  user.status,
    }


@router.get("/users/{user_id}")
def get_user(
    user_id:          int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get one user's details."""
    user = db.query(CompanyUser).filter(
        CompanyUser.id          == user_id,
        CompanyUser.business_id == current_business.id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "id":          user.id,
        "name":        user.name,
        "email":       user.email,
        "role":        user.role,
        "status":      user.status,
        "permissions": user.permissions,
        "invited_at":  user.invited_at,
        "joined_at":   user.joined_at,
        "created_at":  user.created_at,
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id:          int,
    payload:          UserUpdate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Update user name, role, or permissions."""
    user = db.query(CompanyUser).filter(
        CompanyUser.id          == user_id,
        CompanyUser.business_id == current_business.id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.commit()

    log_action(db, current_business.id, current_business.email,
               "user_updated", "company_user", user.id)

    return {"message": "User updated.", "id": user.id, "email": user.email}


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id:          int,
    payload:          UserStatusUpdate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Activate or deactivate a user."""
    user = db.query(CompanyUser).filter(
        CompanyUser.id          == user_id,
        CompanyUser.business_id == current_business.id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.status     = payload.status
    user.updated_at = datetime.utcnow()
    db.commit()

    log_action(db, current_business.id, current_business.email,
               f"user_{payload.status}", "company_user", user.id)

    return {"message": f"User {payload.status}.", "id": user.id, "status": user.status}


@router.post("/invitations/{invitation_id}/resend")
def resend_user_invitation(
    invitation_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Resend a user invitation."""
    user = db.query(CompanyUser).filter(
        CompanyUser.id          == invitation_id,
        CompanyUser.business_id == current_business.id,
        CompanyUser.status      == UserStatusEnum.invited,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Pending invitation not found.")

    user.invited_at = datetime.utcnow()
    db.commit()

    return {"message": f"Invitation resent to {user.email}.", "email": user.email}


@router.delete("/users/{user_id}")
def remove_user(
    user_id:          int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Remove a user from the company."""
    user = db.query(CompanyUser).filter(
        CompanyUser.id          == user_id,
        CompanyUser.business_id == current_business.id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    email = user.email
    db.delete(user)
    db.commit()

    log_action(db, current_business.id, current_business.email,
               "user_removed", "company_user", user_id, email)

    return {"message": f"User {email} removed from company."}


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_security(db, business_id):
    sec = db.query(SecuritySetting).filter(
        SecuritySetting.business_id == business_id
    ).first()
    if not sec:
        sec = SecuritySetting(business_id=business_id)
        db.add(sec)
        db.commit()
        db.refresh(sec)
    return sec


@router.get("/security")
def get_security(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get security settings."""
    sec = get_or_create_security(db, current_business.id)
    return {
        "two_fa_enabled":       sec.two_fa_enabled,
        "two_fa_method":        sec.two_fa_method,
        "session_timeout_mins": sec.session_timeout_mins,
        "login_notifications":  sec.login_notifications,
        "ip_whitelist":         json.loads(sec.ip_whitelist) if sec.ip_whitelist else [],
        "updated_at":           sec.updated_at,
    }


@router.patch("/security")
def update_security(
    payload:          SecurityUpdate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Update security settings."""
    sec = get_or_create_security(db, current_business.id)

    if payload.session_timeout_mins is not None:
        sec.session_timeout_mins = payload.session_timeout_mins
    if payload.login_notifications is not None:
        sec.login_notifications = payload.login_notifications
    if payload.ip_whitelist is not None:
        sec.ip_whitelist = payload.ip_whitelist

    sec.updated_at = datetime.utcnow()
    db.commit()

    log_action(db, current_business.id, current_business.email,
               "security_updated", "security_setting")

    return {"message": "Security settings updated."}


@router.post("/security/2fa/enable")
def enable_2fa(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Enable two-factor authentication."""
    sec = get_or_create_security(db, current_business.id)

    if sec.two_fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")

    # Generate a secret (in production use pyotp)
    secret = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
    sec.two_fa_secret  = secret
    sec.two_fa_enabled = True
    sec.updated_at     = datetime.utcnow()
    db.commit()

    log_action(db, current_business.id, current_business.email, "2fa_enabled")

    return {
        "message": "2FA enabled successfully.",
        "secret":  secret,
        "method":  sec.two_fa_method,
    }


@router.post("/security/2fa/disable")
def disable_2fa(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Disable two-factor authentication."""
    sec = get_or_create_security(db, current_business.id)

    if not sec.two_fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled.")

    sec.two_fa_enabled = False
    sec.two_fa_secret  = None
    sec.updated_at     = datetime.utcnow()
    db.commit()

    log_action(db, current_business.id, current_business.email, "2fa_disabled")

    return {"message": "2FA disabled successfully."}


@router.post("/security/2fa/verify")
def verify_2fa(
    payload:          TwoFAVerify,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Verify a 2FA code."""
    sec = get_or_create_security(db, current_business.id)

    if not sec.two_fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled.")

    # In production: verify with pyotp or email code
    # For now simulate verification
    if len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code. Must be 6 digits.")

    return {"message": "2FA code verified successfully.", "verified": True}


@router.get("/security/sessions")
def get_sessions(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get all active login sessions."""
    sessions = db.query(UserSession).filter(
        UserSession.business_id == current_business.id,
        UserSession.is_active   == True,
    ).order_by(UserSession.last_seen.desc()).all()

    return {
        "total": len(sessions),
        "sessions": [
            {
                "id":         s.id,
                "device":     s.device,
                "browser":    s.browser,
                "ip_address": s.ip_address,
                "location":   s.location,
                "created_at": s.created_at,
                "last_seen":  s.last_seen,
            }
            for s in sessions
        ],
    }


@router.delete("/security/sessions/{session_id}")
def delete_session(
    session_id:       int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Log out one active session."""
    session = db.query(UserSession).filter(
        UserSession.id          == session_id,
        UserSession.business_id == current_business.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session.is_active = False
    db.commit()

    log_action(db, current_business.id, current_business.email,
               "session_terminated", "user_session", session_id)

    return {"message": "Session terminated successfully."}


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_notif_prefs(db, business_id):
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.business_id == business_id
    ).first()
    if not prefs:
        prefs = NotificationPreference(business_id=business_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/notification-preferences")
def get_notification_preferences(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get notification preferences."""
    prefs = get_or_create_notif_prefs(db, current_business.id)
    return {
        "email_notifications": prefs.email_notifications,
        "sms_notifications":   prefs.sms_notifications,
        "filing_deadlines":    prefs.filing_deadlines,
        "document_processed":  prefs.document_processed,
        "auditor_updates":     prefs.auditor_updates,
        "system_alerts":       prefs.system_alerts,
        "weekly_summary":      prefs.weekly_summary,
        "updated_at":          prefs.updated_at,
    }


@router.patch("/notification-preferences")
def update_notification_preferences(
    payload:          NotificationPrefUpdate,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Update notification preferences."""
    prefs = get_or_create_notif_prefs(db, current_business.id)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(prefs, field, value)
    prefs.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Notification preferences updated."}


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/audit-log")
def get_audit_log(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
    skip:             int      = 0,
    limit:            int      = 50,
):
    """Get immutable company activity history."""
    logs = db.query(AuditLog).filter(
        AuditLog.business_id == current_business.id
    ).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    total = db.query(AuditLog).filter(
        AuditLog.business_id == current_business.id
    ).count()

    return {
        "total":  total,
        "skip":   skip,
        "limit":  limit,
        "logs": [
            {
                "id":          l.id,
                "user_email":  l.user_email,
                "action":      l.action,
                "resource":    l.resource,
                "resource_id": l.resource_id,
                "details":     l.details,
                "ip_address":  l.ip_address,
                "created_at":  l.created_at,
            }
            for l in logs
        ],
    }


@router.get("/audit-log/{log_id}")
def get_audit_log_entry(
    log_id:           int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get one audit log record."""
    log = db.query(AuditLog).filter(
        AuditLog.id          == log_id,
        AuditLog.business_id == current_business.id,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log entry not found.")

    return {
        "id":          log.id,
        "user_email":  log.user_email,
        "action":      log.action,
        "resource":    log.resource,
        "resource_id": log.resource_id,
        "details":     log.details,
        "ip_address":  log.ip_address,
        "created_at":  log.created_at,
    }