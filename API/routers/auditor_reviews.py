import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import (
    get_db, Business, AuditorReview, ReviewIssue,
    ReviewIssueAttachment, ReviewIssueStatusEnum, AuditorStatusEnum
)
from dependencies import get_current_business

router = APIRouter(prefix="/auditor-reviews", tags=["Auditor Reviews"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "issue_attachments")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("")
def list_auditor_reviews(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """List all auditor reviews for current business."""
    reviews = db.query(AuditorReview).filter(
        AuditorReview.business_id == current_business.id
    ).order_by(AuditorReview.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "submission_id": r.submission_id,
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at,
            "issues_count": len(r.issues),
        }
        for r in reviews
    ]


@router.get("/{review_id}")
def get_auditor_review_detail(
    review_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get details of an auditor review including issues and attachments."""
    review = db.query(AuditorReview).filter(
        AuditorReview.id == review_id,
        AuditorReview.business_id == current_business.id,
    ).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found.",
        )

    return {
        "id": review.id,
        "submission_id": review.submission_id,
        "status": review.status,
        "notes": review.notes,
        "created_at": review.created_at,
        "issues": [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description,
                "status": i.status,
                "response": i.response,
                "responded_at": i.responded_at,
                "attachments": [
                    {
                        "id": a.id,
                        "file_name": a.file_name,
                        "file_size": a.file_size,
                        "uploaded_at": a.uploaded_at,
                    }
                    for a in i.attachments
                ],
            }
            for i in review.issues
        ],
    }


@router.post("/{review_id}/issues/{issue_id}/respond")
def respond_to_issue(
    review_id: int,
    issue_id: int,
    response: str = Form(...),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Business responds with clarification or notes for an auditor review issue."""
    review = db.query(AuditorReview).filter(
        AuditorReview.id == review_id,
        AuditorReview.business_id == current_business.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    issue = db.query(ReviewIssue).filter(
        ReviewIssue.id == issue_id,
        ReviewIssue.review_id == review_id,
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    issue.response = response
    issue.responded_at = datetime.utcnow()
    issue.status = ReviewIssueStatusEnum.responded
    db.commit()
    db.refresh(issue)

    return {
        "message": "Response submitted successfully.",
        "issue_id": issue.id,
        "status": issue.status,
        "response": issue.response,
        "responded_at": issue.responded_at,
    }


@router.post("/{review_id}/issues/{issue_id}/attachments")
def upload_issue_attachment(
    review_id: int,
    issue_id: int,
    file: UploadFile = File(...),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Upload supporting documentation for an auditor review issue."""
    review = db.query(AuditorReview).filter(
        AuditorReview.id == review_id,
        AuditorReview.business_id == current_business.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    issue = db.query(ReviewIssue).filter(
        ReviewIssue.id == issue_id,
        ReviewIssue.review_id == review_id,
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"issue_{issue_id}_{int(datetime.utcnow().timestamp())}{file_ext}"
    dest_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(dest_path)

    attachment = ReviewIssueAttachment(
        issue_id=issue.id,
        file_name=file.filename,
        file_path=dest_path,
        file_size=file_size,
        file_type=file.content_type,
        uploaded_at=datetime.utcnow(),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "message": "Attachment uploaded successfully.",
        "attachment_id": attachment.id,
        "file_name": attachment.file_name,
        "file_size": attachment.file_size,
    }


@router.post("/{review_id}/resubmit")
def resubmit_review(
    review_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Resubmit package to auditor after addressing review issues."""
    review = db.query(AuditorReview).filter(
        AuditorReview.id == review_id,
        AuditorReview.business_id == current_business.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    review.status = "resubmitted"
    review.updated_at = datetime.utcnow()
    current_business.auditor_status = AuditorStatusEnum.in_review
    db.commit()

    return {
        "message": "Review resubmitted to auditor successfully.",
        "review_id": review.id,
        "status": review.status,
    }
