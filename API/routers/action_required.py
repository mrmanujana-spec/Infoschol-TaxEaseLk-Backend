from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, Business, ActionRequired, IssueStatusEnum
from dependencies import get_current_business
from schemas import ActionRequiredOut, ActionRequiredList

router = APIRouter(prefix="/business/action-required", tags=["Action Required"])


@router.get("", response_model=ActionRequiredList)
def get_action_required_list(
    status_filter: Optional[str] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = db.query(ActionRequired).filter(
        ActionRequired.business_id == current_business.id
    )
    if status_filter:
        query = query.filter(ActionRequired.status == status_filter)
    else:
        query = query.filter(ActionRequired.status == IssueStatusEnum.open)

    issues = query.order_by(ActionRequired.created_at.desc()).all()
    return ActionRequiredList(total=len(issues), issues=issues)


@router.get("/{issue_id}", response_model=ActionRequiredOut)
def get_action_required_item(
    issue_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    issue = db.query(ActionRequired).filter(
        ActionRequired.id == issue_id,
        ActionRequired.business_id == current_business.id,
    ).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item {issue_id} not found.",
        )
    return issue


@router.post("/{issue_id}/resolve", response_model=ActionRequiredOut)
def resolve_action_required(
    issue_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    issue = db.query(ActionRequired).filter(
        ActionRequired.id == issue_id,
        ActionRequired.business_id == current_business.id,
    ).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item {issue_id} not found.",
        )
    issue.status = IssueStatusEnum.resolved
    issue.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)
    return issue
