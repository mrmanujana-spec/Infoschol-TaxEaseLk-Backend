from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from typing import List

from database import (
    get_db, Business, FinancialYear, Document, ActionRequired
)
from dependencies import get_current_business
from schemas import (
    BusinessProfile,
    BusinessUpdate,
    FinancialYearOut,
    SearchOut,
    SearchResultItem,
)

router = APIRouter(prefix="/business", tags=["Business"])


@router.get("/me", response_model=BusinessProfile)
def get_my_business_profile(
    current_business: Business = Depends(get_current_business),
):
    """Retrieve profile and corporate metadata for the authenticated business."""
    return current_business


@router.put("/me", response_model=BusinessProfile)
def update_my_business_profile(
    payload: BusinessUpdate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Update profile fields for the authenticated business."""
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current_business, field, value)

    current_business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_business)
    return current_business


@router.get("/financial-years", response_model=List[FinancialYearOut])
def get_financial_years(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """List all financial years recorded for this business."""
    years = db.query(FinancialYear).filter(
        FinancialYear.business_id == current_business.id
    ).order_by(FinancialYear.start_date.desc()).all()

    return years


@router.get("/search", response_model=SearchOut)
def global_search(
    q: str = Query(..., min_length=1, description="Keyword to search across documents and issues"),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Search documents and open action items matching query text."""
    bid = current_business.id
    keyword = f"%{q.strip()}%"

    matched_docs = db.query(Document).filter(
        Document.business_id == bid,
        or_(
            Document.name.ilike(keyword),
            Document.doc_type.ilike(keyword),
            Document.extraction_notes.ilike(keyword),
        ),
    ).all()

    matched_issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == bid,
        or_(
            ActionRequired.title.ilike(keyword),
            ActionRequired.description.ilike(keyword),
        ),
    ).all()

    results: List[SearchResultItem] = []
    for d in matched_docs:
        results.append(SearchResultItem(
            type="document",
            id=d.id,
            title=d.name,
            description=f"Type: {d.doc_type} | Status: {d.status}",
            url=f"/documents/{d.id}",
        ))

    for i in matched_issues:
        results.append(SearchResultItem(
            type="issue",
            id=i.id,
            title=i.title,
            description=i.description[:100] if i.description else None,
            url=f"/business/action-required/{i.id}",
        ))

    return SearchOut(query=q, results=results, total=len(results))
