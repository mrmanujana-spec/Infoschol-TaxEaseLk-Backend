import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
try:
    from ..database import get_db, Business, FinancialYear, Document, ActionRequired, Notification
    from ..auth import get_current_business
    from ..schemas import (
        BusinessProfile, BusinessUpdate,
        FinancialYearOut,
        SearchOut, SearchResult,
    )
except ImportError:
    from database import get_db, Business, FinancialYear, Document, ActionRequired, Notification
    from auth import get_current_business
    from schemas import (
    BusinessProfile, BusinessUpdate,
    FinancialYearOut,
    SearchOut, SearchResult,
)

router = APIRouter(prefix="/business", tags=["Business"])


@router.get("/me", response_model=BusinessProfile)
def get_me(current_business: Business = Depends(get_current_business)):
    return current_business


@router.put("/me", response_model=BusinessProfile)
def update_me(
    payload: BusinessUpdate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current_business, field, value)
    current_business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_business)
    return current_business


@router.get("/financial-years", response_model=list[FinancialYearOut])
def get_financial_years(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    return (
        db.query(FinancialYear)
        .filter(FinancialYear.business_id == current_business.id)
        .order_by(FinancialYear.start_date.desc())
        .all()
    )


@router.get("/search", response_model=SearchOut)
def search(
    q: str = Query(..., min_length=1),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    bid = current_business.id
    results = []

    docs = db.query(Document).filter(
        Document.business_id == bid,
        or_(Document.name.ilike(f"%{q}%"), Document.doc_type.ilike(f"%{q}%"))
    ).limit(5).all()
    for d in docs:
        results.append(SearchResult(type="document", id=d.id, title=d.name,
                                    description=d.doc_type, url=f"/business/documents/{d.id}"))

    issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == bid,
        or_(ActionRequired.title.ilike(f"%{q}%"), ActionRequired.description.ilike(f"%{q}%"))
    ).limit(5).all()
    for i in issues:
        results.append(SearchResult(type="issue", id=i.id, title=i.title,
                                    description=i.description[:80], url=f"/business/action-required/{i.id}"))

    notifs = db.query(Notification).filter(
        Notification.business_id == bid,
        or_(Notification.title.ilike(f"%{q}%"), Notification.message.ilike(f"%{q}%"))
    ).limit(5).all()
    for n in notifs:
        results.append(SearchResult(type="notification", id=n.id, title=n.title,
                                    description=n.message[:80], url=f"/notifications/{n.id}"))

    return SearchOut(query=q, results=results, total=len(results))