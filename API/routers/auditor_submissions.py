import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from io import BytesIO

from database import (
    get_db, Business, Document, ExtractedValue,
    AuditorSubmission, SubmissionHistory, ActionRequired,
    SubmissionStatusEnum, IssueStatusEnum
)
from auth import get_current_business

router = APIRouter(prefix="/auditor-submissions", tags=["Auditor Submissions"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateSubmissionRequest(BaseModel):
    title:             str
    financial_year_id: Optional[int] = None
    notes:             Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_submission_or_404(db: Session, submission_id: int, business_id: int) -> AuditorSubmission:
    s = db.query(AuditorSubmission).filter(
        AuditorSubmission.id          == submission_id,
        AuditorSubmission.business_id == business_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found.")
    return s

def add_history(db: Session, submission_id: int, event: str, message: str):
    h = SubmissionHistory(submission_id=submission_id, event=event, message=message)
    db.add(h)
    db.commit()

def format_submission(s: AuditorSubmission):
    return {
        "id":                s.id,
        "title":             s.title,
        "status":            s.status,
        "financial_year_id": s.financial_year_id,
        "notes":             s.notes,
        "submitted_at":      s.submitted_at,
        "created_at":        s.created_at,
        "updated_at":        s.updated_at,
    }


# ─── POST /auditor-submissions ────────────────────────────────────────────────

@router.post("", status_code=201)
def create_submission(
    payload:          CreateSubmissionRequest,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Create a submission package from documents and extracted financial data."""
    submission = AuditorSubmission(
        business_id       = current_business.id,
        financial_year_id = payload.financial_year_id,
        title             = payload.title,
        notes             = payload.notes,
        status            = SubmissionStatusEnum.draft,
        created_at        = datetime.utcnow(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    add_history(db, submission.id, "created",
                f"Submission '{payload.title}' created as draft.")

    return {
        "message": "Submission package created successfully.",
        **format_submission(submission),
    }


# ─── GET /auditor-submissions ─────────────────────────────────────────────────

@router.get("")
def get_submissions(
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get all previous auditor submissions for this business."""
    submissions = (
        db.query(AuditorSubmission)
        .filter(AuditorSubmission.business_id == current_business.id)
        .order_by(AuditorSubmission.created_at.desc())
        .all()
    )
    return {
        "total":       len(submissions),
        "submissions": [format_submission(s) for s in submissions],
    }


# ─── GET /auditor-submissions/{submission_id} ─────────────────────────────────

@router.get("/{submission_id}")
def get_submission(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get submission details and current status."""
    s = get_submission_or_404(db, submission_id, current_business.id)
    return format_submission(s)


# ─── GET /auditor-submissions/{submission_id}/validation ──────────────────────

@router.get("/{submission_id}/validation")
def get_submission_validation(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Check missing documents and unresolved issues before submitting."""
    s   = get_submission_or_404(db, submission_id, current_business.id)
    bid = current_business.id

    # Check missing required documents
    all_docs      = db.query(Document).filter(Document.business_id == bid).all()
    missing_docs  = [d for d in all_docs if d.is_required and not d.is_uploaded]

    # Check unresolved issues
    open_issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == bid,
        ActionRequired.status      == IssueStatusEnum.open,
    ).all()

    # Check unprocessed documents
    unprocessed = [d for d in all_docs if d.is_uploaded and d.status != "processed"]

    is_ready = len(missing_docs) == 0 and len(open_issues) == 0 and len(unprocessed) == 0

    return {
        "submission_id": submission_id,
        "is_ready":      is_ready,
        "missing_documents": [
            {"id": d.id, "name": d.name, "doc_type": d.doc_type}
            for d in missing_docs
        ],
        "unresolved_issues": [
            {"id": i.id, "title": i.title, "severity": i.severity}
            for i in open_issues
        ],
        "unprocessed_documents": [
            {"id": d.id, "name": d.name, "status": d.status}
            for d in unprocessed
        ],
        "summary": {
            "missing_docs_count":  len(missing_docs),
            "open_issues_count":   len(open_issues),
            "unprocessed_count":   len(unprocessed),
        },
    }


# ─── POST /auditor-submissions/{submission_id}/submit ─────────────────────────

@router.post("/{submission_id}/submit")
def submit_to_auditor(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Submit the package to the auditor."""
    s = get_submission_or_404(db, submission_id, current_business.id)

    if s.status == SubmissionStatusEnum.submitted:
        raise HTTPException(status_code=400, detail="Already submitted.")

    if s.status == SubmissionStatusEnum.approved:
        raise HTTPException(status_code=400, detail="Already approved.")

    # Run validation check
    bid         = current_business.id
    missing_docs = db.query(Document).filter(
        Document.business_id == bid,
        Document.is_required == True,
        Document.is_uploaded == False,
    ).count()

    open_issues = db.query(ActionRequired).filter(
        ActionRequired.business_id == bid,
        ActionRequired.status      == IssueStatusEnum.open,
        ActionRequired.severity    == "error",
    ).count()

    if missing_docs > 0:
        raise HTTPException(status_code=400,
            detail=f"Cannot submit: {missing_docs} required documents are missing.")

    if open_issues > 0:
        raise HTTPException(status_code=400,
            detail=f"Cannot submit: {open_issues} critical issues must be resolved first.")

    # Submit
    s.status       = SubmissionStatusEnum.submitted
    s.submitted_at = datetime.utcnow()
    s.updated_at   = datetime.utcnow()
    db.commit()

    add_history(db, s.id, "submitted",
                f"Package submitted to auditor on {s.submitted_at.strftime('%Y-%m-%d %H:%M')}.")

    return {
        "message":      "Package submitted to auditor successfully.",
        "submitted_at": s.submitted_at,
        **format_submission(s),
    }


# ─── GET /auditor-submissions/{submission_id}/documents ───────────────────────

@router.get("/{submission_id}/documents")
def get_submission_documents(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get all documents included in this submission package."""
    s    = get_submission_or_404(db, submission_id, current_business.id)
    docs = db.query(Document).filter(
        Document.business_id       == current_business.id,
        Document.financial_year_id == s.financial_year_id,
        Document.is_uploaded       == True,
    ).all()

    return {
        "submission_id": submission_id,
        "total":         len(docs),
        "documents": [
            {
                "id":           d.id,
                "name":         d.name,
                "doc_type":     d.doc_type,
                "status":       d.status,
                "file_name":    d.file_name,
                "file_size":    d.file_size,
                "uploaded_at":  d.uploaded_at,
                "processed_at": d.processed_at,
            }
            for d in docs
        ],
    }


# ─── GET /auditor-submissions/{submission_id}/financials ──────────────────────

@router.get("/{submission_id}/financials")
def get_submission_financials(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get financial data included in this submission package."""
    s = get_submission_or_404(db, submission_id, current_business.id)

    values = (
        db.query(ExtractedValue)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(
            Document.business_id       == current_business.id,
            Document.financial_year_id == s.financial_year_id,
        )
        .all()
    )

    def get_val(name):
        for v in values:
            if v.field_name == name:
                try: return float(v.value)
                except: return 0.0
        return 0.0

    return {
        "submission_id":      submission_id,
        "financial_year_id":  s.financial_year_id,
        "total_values":       len(values),
        "summary": {
            "total_revenue":      get_val("total_revenue"),
            "total_expenses":     get_val("total_expenses"),
            "accounting_profit":  get_val("accounting_profit"),
            "tax_paid":           get_val("tax_paid"),
        },
        "values": [
            {
                "id":         v.id,
                "field_name": v.field_name,
                "value":      v.value,
                "confidence": v.confidence,
                "page":       v.page,
            }
            for v in values
        ],
    }


# ─── GET /auditor-submissions/{submission_id}/download ────────────────────────

@router.get("/{submission_id}/download")
def download_submission_package(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Download the complete auditor package as a PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="Run: pip install reportlab")

    s    = get_submission_or_404(db, submission_id, current_business.id)
    docs = db.query(Document).filter(
        Document.business_id       == current_business.id,
        Document.financial_year_id == s.financial_year_id,
        Document.is_uploaded       == True,
    ).all()

    values = (
        db.query(ExtractedValue)
        .join(Document, ExtractedValue.document_id == Document.id)
        .filter(
            Document.business_id       == current_business.id,
            Document.financial_year_id == s.financial_year_id,
        )
        .all()
    )

    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story  = [
        Paragraph("TaxEase LK – Auditor Submission Package", styles["Title"]),
        Paragraph(f"Company: {current_business.company_name}", styles["Heading2"]),
        Paragraph(f"Submission: {s.title}", styles["Normal"]),
        Paragraph(f"Status: {s.status.value.upper()}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 20),
        Paragraph("Documents Included", styles["Heading2"]),
    ]

    doc_data = [["#", "Document Name", "Type", "Status"]]
    for i, d in enumerate(docs, 1):
        doc_data.append([str(i), d.name, d.doc_type, d.status])

    doc_table = Table(doc_data, colWidths=[30, 200, 150, 100])
    doc_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Financial Values", styles["Heading2"]))

    val_data = [["Field", "Value (LKR)", "Confidence", "Page"]]
    for v in values:
        val_data.append([
            v.field_name.replace("_", " ").title(),
            v.value or "-",
            f"{int((v.confidence or 0) * 100)}%" if v.confidence else "-",
            str(v.page) if v.page else "-",
        ])

    val_table = Table(val_data, colWidths=[180, 120, 80, 50])
    val_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(val_table)
    doc.build(story)
    buffer.seek(0)

    filename = f"AuditorPackage_{s.title.replace(' ','_')}_{submission_id}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ─── GET /auditor-submissions/{submission_id}/history ─────────────────────────

@router.get("/{submission_id}/history")
def get_submission_history(
    submission_id:    int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get the full history of events for this submission."""
    s = get_submission_or_404(db, submission_id, current_business.id)

    history = (
        db.query(SubmissionHistory)
        .filter(SubmissionHistory.submission_id == submission_id)
        .order_by(SubmissionHistory.created_at.desc())
        .all()
    )

    return {
        "submission_id": submission_id,
        "title":         s.title,
        "status":        s.status,
        "total":         len(history),
        "history": [
            {
                "id":         h.id,
                "event":      h.event,
                "message":    h.message,
                "created_at": h.created_at,
            }
            for h in history
        ],
    }
