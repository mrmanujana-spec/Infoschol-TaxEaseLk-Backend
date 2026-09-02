import os
from io import BytesIO
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import (
    get_db, Business, FinancialYear, Document, ExtractedValue,
    AuditorSubmission, SubmissionHistory, ActionRequired,
    SubmissionStatusEnum, AuditorStatusEnum, IssueStatusEnum
)
from dependencies import get_current_business
from schemas import (
    CreateSubmissionRequest,
    AuditorSubmissionOut,
    AuditorSubmissionList,
)

router = APIRouter(prefix="/auditor-submissions", tags=["Auditor Submissions"])


@router.get("", response_model=AuditorSubmissionList)
def list_submissions(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """List all auditor submissions created by the current business."""
    submissions = db.query(AuditorSubmission).filter(
        AuditorSubmission.business_id == current_business.id
    ).order_by(AuditorSubmission.created_at.desc()).all()

    return AuditorSubmissionList(total=len(submissions), submissions=submissions)


@router.post("", response_model=AuditorSubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: CreateSubmissionRequest,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Create a draft submission package."""
    fy_id = payload.financial_year_id
    if not fy_id:
        current_fy = db.query(FinancialYear).filter(
            FinancialYear.business_id == current_business.id,
            FinancialYear.is_current == True,
        ).first()
        fy_id = current_fy.id if current_fy else None

    title = payload.title or f"Tax Filing Package - {datetime.utcnow().year}"
    sub = AuditorSubmission(
        business_id=current_business.id,
        financial_year_id=fy_id,
        title=title,
        notes=payload.notes,
        status=SubmissionStatusEnum.draft,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    hist = SubmissionHistory(
        submission_id=sub.id,
        event="created",
        message="Draft submission package created.",
    )
    db.add(hist)
    db.commit()

    return sub


@router.get("/{submission_id}", response_model=AuditorSubmissionOut)
def get_submission(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    sub = db.query(AuditorSubmission).filter(
        AuditorSubmission.id == submission_id,
        AuditorSubmission.business_id == current_business.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission package not found.")
    return sub


@router.get("/{submission_id}/validation")
def validate_submission(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Check if all required documents and issues are resolved before submission."""
    sub = db.query(AuditorSubmission).filter(
        AuditorSubmission.id == submission_id,
        AuditorSubmission.business_id == current_business.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission package not found.")

    docs = db.query(Document).filter(Document.business_id == current_business.id).all()
    missing_docs = [d.name for d in docs if d.is_required and not d.is_uploaded]

    issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == current_business.id,
        ActionRequired.status == IssueStatusEnum.open,
    ).all()

    can_submit = len(missing_docs) == 0 and len(issues) == 0

    return {
        "submission_id": sub.id,
        "is_ready_to_submit": can_submit,
        "missing_required_documents": missing_docs,
        "open_action_items_count": len(issues),
        "total_documents": len(docs),
    }


@router.post("/{submission_id}/submit", response_model=AuditorSubmissionOut)
def submit_to_auditor(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Submit package for auditor review."""
    sub = db.query(AuditorSubmission).filter(
        AuditorSubmission.id == submission_id,
        AuditorSubmission.business_id == current_business.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission package not found.")

    sub.status = SubmissionStatusEnum.submitted
    sub.submitted_at = datetime.utcnow()
    current_business.auditor_status = AuditorStatusEnum.in_review

    hist = SubmissionHistory(
        submission_id=sub.id,
        event="submitted",
        message="Package formally submitted for auditor review.",
    )
    db.add(hist)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/{submission_id}/documents")
def get_submission_documents(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).filter(Document.business_id == current_business.id).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "doc_type": d.doc_type,
            "is_uploaded": d.is_uploaded,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "status": d.status,
            "uploaded_at": d.uploaded_at,
        }
        for d in docs
    ]


@router.get("/{submission_id}/financials")
def get_submission_financials(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    sub = db.query(AuditorSubmission).filter(
        AuditorSubmission.id == submission_id,
        AuditorSubmission.business_id == current_business.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission package not found.")

    fy = db.query(FinancialYear).filter(
        FinancialYear.business_id == current_business.id,
        FinancialYear.id == sub.financial_year_id if sub.financial_year_id else True,
    ).first()

    return {
        "financial_year": fy.year_label if fy else "Current",
        "accounting_profit": fy.accounting_profit if fy else 0.0,
        "taxable_income": fy.taxable_income if fy else 0.0,
        "estimated_cit": fy.estimated_cit if fy else 0.0,
    }


@router.get("/{submission_id}/history")
def get_submission_history(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    hist = db.query(SubmissionHistory).filter(
        SubmissionHistory.submission_id == submission_id
    ).order_by(SubmissionHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "event": h.event,
            "message": h.message,
            "created_at": h.created_at,
        }
        for h in hist
    ]


@router.get("/{submission_id}/download")
def download_submission_pdf(
    submission_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Generate and stream a downloadable audit submission summary PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation requires reportlab.")

    sub = db.query(AuditorSubmission).filter(
        AuditorSubmission.id == submission_id,
        AuditorSubmission.business_id == current_business.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"TaxEase LK – Audit Package: {sub.title}", styles["Title"]),
        Paragraph(f"Company: {current_business.company_name}", styles["Heading2"]),
        Paragraph(f"Status: {sub.status.value.replace('_', ' ').title()}", styles["Normal"]),
        Paragraph(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 20),
    ]

    table_data = [
        ["Field", "Value"],
        ["Company Name", current_business.company_name],
        ["Registration No", current_business.registration_number or "N/A"],
        ["TIN", current_business.tin or "N/A"],
        ["Assigned Auditor", current_business.auditor_name or "Unassigned"],
    ]
    table = Table(table_data, colWidths=[200, 250])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)

    filename = f"Submission_Package_{submission_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
