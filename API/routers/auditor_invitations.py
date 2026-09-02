from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from database import (
    get_db, Business, FinancialYear, AuditorInvitation,
    InvitationStatusEnum, AuditorStatusEnum, AuditLog
)
from dependencies import get_current_business
from schemas import (
    AuditorInvitationCreate,
    AuditorInvitationOut,
    AuditorInvitationList,
    MessageOut,
)

router = APIRouter(prefix="/auditor-invitations", tags=["Auditor Invitations"])


@router.get("", response_model=AuditorInvitationList)
def list_invitations(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """List all auditor invitations sent by the current business."""
    invitations = db.query(AuditorInvitation).filter(
        AuditorInvitation.business_id == current_business.id
    ).order_by(AuditorInvitation.created_at.desc()).all()

    return AuditorInvitationList(total=len(invitations), invitations=invitations)


@router.post("", response_model=AuditorInvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: AuditorInvitationCreate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Send an invitation to an external tax auditor."""
    # Check if there is an active pending invitation for this email
    existing = db.query(AuditorInvitation).filter(
        AuditorInvitation.business_id == current_business.id,
        AuditorInvitation.auditor_email == payload.auditor_email,
        AuditorInvitation.status == InvitationStatusEnum.pending,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active pending invitation for {payload.auditor_email} already exists.",
        )

    invitation = AuditorInvitation(
        business_id=current_business.id,
        financial_year_id=payload.financial_year_id,
        auditor_name=payload.auditor_name,
        auditor_email=payload.auditor_email,
        auditor_firm=payload.auditor_firm,
        message=payload.message,
        status=InvitationStatusEnum.pending,
        sent_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(invitation)

    # Update business auditor name and status
    current_business.auditor_name = payload.auditor_name
    current_business.auditor_status = AuditorStatusEnum.pending

    # Log audit event
    log = AuditLog(
        business_id=current_business.id,
        user_email=current_business.email,
        action="auditor_invited",
        resource="auditor_invitation",
        details=f"Invited auditor {payload.auditor_name} ({payload.auditor_email})",
        created_at=datetime.utcnow(),
    )
    db.add(log)

    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/{invitation_id}", response_model=AuditorInvitationOut)
def get_invitation(
    invitation_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve details for a specific invitation."""
    invitation = db.query(AuditorInvitation).filter(
        AuditorInvitation.id == invitation_id,
        AuditorInvitation.business_id == current_business.id,
    ).first()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invitation {invitation_id} not found.",
        )
    return invitation


@router.post("/{invitation_id}/resend", response_model=AuditorInvitationOut)
def resend_invitation(
    invitation_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Resend a pending auditor invitation with a fresh expiration date."""
    invitation = db.query(AuditorInvitation).filter(
        AuditorInvitation.id == invitation_id,
        AuditorInvitation.business_id == current_business.id,
    ).first()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invitation {invitation_id} not found.",
        )

    invitation.sent_at = datetime.utcnow()
    invitation.expires_at = datetime.utcnow() + timedelta(days=14)
    invitation.status = InvitationStatusEnum.pending
    db.commit()
    db.refresh(invitation)
    return invitation


@router.delete("/{invitation_id}", response_model=MessageOut)
def cancel_invitation(
    invitation_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Cancel a pending auditor invitation."""
    invitation = db.query(AuditorInvitation).filter(
        AuditorInvitation.id == invitation_id,
        AuditorInvitation.business_id == current_business.id,
    ).first()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invitation {invitation_id} not found.",
        )

    invitation.status = InvitationStatusEnum.cancelled
    invitation.cancelled_at = datetime.utcnow()
    db.commit()
    return {"message": "Invitation cancelled successfully."}
