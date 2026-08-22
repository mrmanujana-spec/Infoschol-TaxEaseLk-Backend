import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
try:
    from ..database import get_db, Business, ActionRequired, IssueStatusEnum
    from ..auth import get_current_business
    from ..schemas import ActionRequiredOut, ActionRequiredList
except ImportError:
    from database import get_db, Business, ActionRequired, IssueStatusEnum
    from auth import get_current_business
    from schemas import ActionRequiredOut, ActionRequiredList

router = APIRouter(prefix="/business", tags=["Action Required"])


@router.get("/action-required", response_model=ActionRequiredList)
def get_all_issues(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    issues = (
        db.query(ActionRequired)
        .filter(ActionRequired.business_id == current_business.id)
        .order_by(ActionRequired.severity.desc(), ActionRequired.created_at.desc())
        .all()
    )
    return ActionRequiredList(total=len(issues), issues=issues)


@router.get("/action-required/{issue_id}", response_model=ActionRequiredOut)
def get_issue(
    issue_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    issue = db.query(ActionRequired).filter(
        ActionRequired.id == issue_id,
        ActionRequired.business_id == current_business.id,
    ).first()

    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Issue {issue_id} not found.")
    return issue