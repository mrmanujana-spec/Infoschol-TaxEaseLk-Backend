import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import shutil, uuid

from database import (
    get_db, Business, AuditorReview, ReviewIssue,
    ReviewIssueAttachment, ReviewIssueStatusEnum,
    AuditorSubmission, SubmissionStatusEnum
)
from auth import get_current_business

router = APIRouter(prefix="/auditor-reviews", tags=["Auditor Reviews"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class IssueResponseRequest(BaseModel):
    response: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_review_or_404(db, review_id, business_id):
    r = db.query(AuditorReview).filter(
        AuditorReview.id          == review_id,
        AuditorReview.business_id == business_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found.")
    return r

def get_issue_or_404(db, review_id, issue_id):
    issue = db.query(ReviewIssue).filter(
        ReviewIssue.id        == issue_id,
        ReviewIssue.review_id == review_id,
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found in review {review_id}.")
    return issue


# ─── POST /auditor-reviews/{review_id}/issues/{issue_id}/respond ──────────────

@router.post("/{review_id}/issues/{issue_id}/respond")
def respond_to_issue(
    review_id:        int,
    issue_id:         int,
    payload:          IssueResponseRequest,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Business responds to an auditor issue."""
    review = get_review_or_404(db, review_id, current_business.id)
    issue  = get_issue_or_404(db, review_id, issue_id)

    if issue.status == ReviewIssueStatusEnum.resolved:
        raise HTTPException(status_code=400, detail="Issue is already resolved.")

    issue.response     = payload.response
    issue.status       = ReviewIssueStatusEnum.responded
    issue.responded_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)

    return {
        "message":      "Response submitted successfully.",
        "issue_id":     issue.id,
        "review_id":    review_id,
        "status":       issue.status,
        "response":     issue.response,
        "responded_at": issue.responded_at,
    }


# ─── POST /auditor-reviews/{review_id}/issues/{issue_id}/attachments ──────────

@router.post("/{review_id}/issues/{issue_id}/attachments", status_code=201)
async def upload_issue_attachment(
    review_id:        int,
    issue_id:         int,
    file:             UploadFile = File(...),
    current_business: Business   = Depends(get_current_business),
    db:               Session    = Depends(get_db),
):
    """Business uploads supporting documentation for an auditor issue."""
    review = get_review_or_404(db, review_id, current_business.id)
    issue  = get_issue_or_404(db, review_id, issue_id)

    # Validate file type
    allowed_types = [
        "application/pdf", "image/jpeg", "image/png",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed.")

    # Save file
    ext         = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_dir    = os.path.join(UPLOAD_DIR, str(current_business.id), "review_attachments")
    os.makedirs(save_dir, exist_ok=True)
    save_path   = os.path.join(save_dir, unique_name)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(save_path)

    # Save to DB
    attachment = ReviewIssueAttachment(
        issue_id    = issue.id,
        file_name   = file.filename,
        file_path   = save_path,
        file_size   = file_size,
        file_type   = file.content_type,
        uploaded_at = datetime.utcnow(),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "message":     "Attachment uploaded successfully.",
        "id":          attachment.id,
        "issue_id":    issue_id,
        "review_id":   review_id,
        "file_name":   attachment.file_name,
        "file_size":   attachment.file_size,
        "file_type":   attachment.file_type,
        "uploaded_at": attachment.uploaded_at,
    }


# ─── POST /auditor-reviews/{review_id}/resubmit ───────────────────────────────

@router.post("/{review_id}/resubmit")
def resubmit_review(
    review_id:        int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Resubmit responses and documents to the auditor after addressing issues."""
    review = get_review_or_404(db, review_id, current_business.id)

    # Check all issues have been responded to
    open_issues = db.query(ReviewIssue).filter(
        ReviewIssue.review_id == review_id,
        ReviewIssue.status    == ReviewIssueStatusEnum.open,
    ).all()

    if open_issues:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resubmit: {len(open_issues)} issue(s) still need a response.",
        )

    # Update review status
    review.status     = "resubmitted"
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)

    # Count responded issues
    responded = db.query(ReviewIssue).filter(
        ReviewIssue.review_id == review_id,
        ReviewIssue.status    == ReviewIssueStatusEnum.responded,
    ).count()

    attachments = db.query(ReviewIssueAttachment).join(
        ReviewIssue, ReviewIssueAttachment.issue_id == ReviewIssue.id
    ).filter(ReviewIssue.review_id == review_id).count()

    return {
        "message":             "Resubmitted to auditor successfully.",
        "review_id":           review_id,
        "status":              review.status,
        "responded_issues":    responded,
        "total_attachments":   attachments,
        "resubmitted_at":      review.updated_at,
    }