import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import shutil
import uuid

from database import get_db, Business, Document, FinancialYear, ExtractedValue, DocumentHistory
from auth import get_current_business

router = APIRouter(prefix="/documents", tags=["Documents"])

# ── Upload folder ─────────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── GET /documents ───────────────────────────────────────────────────────────
@router.get("")
def get_documents(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get document table for the selected company and financial year."""
    query = db.query(Document).filter(Document.business_id == current_business.id)

    if financial_year_id:
        query = query.filter(Document.financial_year_id == financial_year_id)

    docs = query.order_by(Document.created_at.desc()).all()

    return {
        "total": len(docs),
        "documents": [
            {
                "id":           d.id,
                "name":         d.name,
                "doc_type":     d.doc_type,
                "status":       d.status,
                "is_uploaded":  d.is_uploaded,
                "is_required":  d.is_required,
                "file_size":    d.file_size,
                "file_type":    d.file_type,
                "uploaded_at":  d.uploaded_at,
                "processed_at": d.processed_at,
                "created_at":   d.created_at,
            }
            for d in docs
        ],
    }


# ─── GET /documents/summary ───────────────────────────────────────────────────
@router.get("/summary")
def get_documents_summary(
    financial_year_id: Optional[int] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get summary cards: uploaded, processed, review required, missing."""
    query = db.query(Document).filter(Document.business_id == current_business.id)
    if financial_year_id:
        query = query.filter(Document.financial_year_id == financial_year_id)

    docs = query.all()

    uploaded        = sum(1 for d in docs if d.is_uploaded)
    processed       = sum(1 for d in docs if d.status == "processed")
    review_required = sum(1 for d in docs if d.status == "review_required")
    missing         = sum(1 for d in docs if d.is_required and not d.is_uploaded)

    return {
        "uploaded":        {"count": uploaded,        "label": "Uploaded"},
        "processed":       {"count": processed,       "label": "Processed"},
        "review_required": {"count": review_required, "label": "Review Required"},
        "missing":         {"count": missing,         "label": "Missing"},
        "total":           len(docs),
    }


# ─── POST /documents ──────────────────────────────────────────────────────────
@router.post("", status_code=201)
async def upload_document(
    file:              UploadFile = File(...),
    doc_type:          str        = Form(...),
    name:              str        = Form(...),
    financial_year_id: Optional[int] = Form(None),
    current_business:  Business   = Depends(get_current_business),
    db:                Session    = Depends(get_db),
):
    """Upload a financial document and trigger AI extraction."""

    # ── Validate file type ────────────────────────────────────────────────────
    allowed_types = ["application/pdf", "image/jpeg", "image/png",
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     "application/vnd.ms-excel"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400,
            detail="Only PDF, JPG, PNG, and Excel files are allowed.")

    # ── Save file to disk ─────────────────────────────────────────────────────
    ext       = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, str(current_business.id), unique_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(save_path)

    # ── Save to DB ────────────────────────────────────────────────────────────
    doc = Document(
        business_id=current_business.id,
        financial_year_id=financial_year_id,
        name=name,
        doc_type=doc_type,
        file_path=save_path,
        file_name=file.filename,
        file_size=file_size,
        file_type=file.content_type,
        is_uploaded=True,
        is_required=True,
        status="processing",
        uploaded_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # ── Add history entry ─────────────────────────────────────────────────────
    _add_history(db, doc.id, "uploaded", f"Document '{name}' uploaded successfully.")

    # ── Trigger AI extraction (background) ───────────────────────────────────
    _trigger_extraction(db, doc)

    return {
        "id":          doc.id,
        "name":        doc.name,
        "status":      doc.status,
        "uploaded_at": doc.uploaded_at,
        "message":     "Document uploaded. AI extraction started.",
    }


# ─── GET /documents/{document_id} ─────────────────────────────────────────────
@router.get("/{document_id}")
def get_document(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get one document's full details for the View Document modal."""
    doc = _get_doc_or_404(db, document_id, current_business.id)

    return {
        "id":               doc.id,
        "name":             doc.name,
        "doc_type":         doc.doc_type,
        "status":           doc.status,
        "is_uploaded":      doc.is_uploaded,
        "is_required":      doc.is_required,
        "file_name":        doc.file_name,
        "file_size":        doc.file_size,
        "file_type":        doc.file_type,
        "financial_year_id":doc.financial_year_id,
        "uploaded_at":      doc.uploaded_at,
        "processed_at":     doc.processed_at,
        "created_at":       doc.created_at,
        "extraction_notes": doc.extraction_notes,
    }


# ─── GET /documents/{document_id}/extracted-values ────────────────────────────
@router.get("/{document_id}/extracted-values")
def get_extracted_values(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get AI-extracted financial values from the document."""
    doc = _get_doc_or_404(db, document_id, current_business.id)

    if doc.status == "processing":
        return {"status": "processing", "message": "AI extraction still in progress.", "values": None}

    if doc.status == "failed":
        return {"status": "failed", "message": "Extraction failed. Use /retry to try again.", "values": None}

    extracted = db.query(ExtractedValue).filter(
        ExtractedValue.document_id == document_id
    ).all()

    return {
        "status":      doc.status,
        "document_id": document_id,
        "extracted_at": doc.processed_at,
        "values": [
            {
                "id":         e.id,
                "field_name": e.field_name,
                "value":      e.value,
                "confidence": e.confidence,
                "page":       e.page,
                "notes":      e.notes,
            }
            for e in extracted
        ],
    }


# ─── GET /documents/{document_id}/source ──────────────────────────────────────
@router.get("/{document_id}/source")
def view_document_source(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """View / preview the original document in the browser."""
    doc = _get_doc_or_404(db, document_id, current_business.id)
    _check_file_exists(doc)

    return FileResponse(
        path=doc.file_path,
        media_type=doc.file_type or "application/octet-stream",
        filename=doc.file_name,
    )


# ─── GET /documents/{document_id}/download ────────────────────────────────────
@router.get("/{document_id}/download")
def download_document(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Download the original document file."""
    doc = _get_doc_or_404(db, document_id, current_business.id)
    _check_file_exists(doc)

    return FileResponse(
        path=doc.file_path,
        media_type="application/octet-stream",
        filename=doc.file_name,
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )


# ─── GET /documents/{document_id}/history ─────────────────────────────────────
@router.get("/{document_id}/history")
def get_document_history(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Get the full processing history of a document."""
    _get_doc_or_404(db, document_id, current_business.id)

    history = db.query(DocumentHistory).filter(
        DocumentHistory.document_id == document_id
    ).order_by(DocumentHistory.created_at.desc()).all()

    return {
        "document_id": document_id,
        "total":       len(history),
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


# ─── POST /documents/{document_id}/replace ────────────────────────────────────
@router.post("/{document_id}/replace", status_code=200)
async def replace_document(
    document_id:      int,
    file:             UploadFile = File(...),
    current_business: Business   = Depends(get_current_business),
    db:               Session    = Depends(get_db),
):
    """Replace an existing document with a new file and re-run AI extraction."""
    doc = _get_doc_or_404(db, document_id, current_business.id)

    # Delete old file if exists
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Save new file
    ext         = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path   = os.path.join(UPLOAD_DIR, str(current_business.id), unique_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Delete old extracted values
    db.query(ExtractedValue).filter(ExtractedValue.document_id == doc.id).delete()

    # Update document record
    doc.file_path    = save_path
    doc.file_name    = file.filename
    doc.file_size    = os.path.getsize(save_path)
    doc.file_type    = file.content_type
    doc.status       = "processing"
    doc.processed_at = None
    doc.uploaded_at  = datetime.utcnow()
    db.commit()

    _add_history(db, doc.id, "replaced", f"Document replaced with '{file.filename}'.")
    _trigger_extraction(db, doc)

    return {"message": "Document replaced. AI extraction restarted.", "id": doc.id, "status": doc.status}


# ─── POST /documents/{document_id}/retry ──────────────────────────────────────
@router.post("/{document_id}/retry", status_code=200)
def retry_document(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Retry AI extraction for a failed document."""
    doc = _get_doc_or_404(db, document_id, current_business.id)

    if doc.status not in ("failed", "review_required"):
        raise HTTPException(status_code=400,
            detail=f"Document status is '{doc.status}'. Only failed or review_required documents can be retried.")

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400,
            detail="Original file not found. Please replace the document instead.")

    doc.status = "processing"
    db.commit()

    _add_history(db, doc.id, "retry", "AI extraction retried by user.")
    _trigger_extraction(db, doc)

    return {"message": "Retry started. AI extraction is running again.", "id": doc.id, "status": doc.status}


# ─── DELETE /documents/{document_id} ──────────────────────────────────────────
@router.delete("/{document_id}", status_code=200)
def delete_document(
    document_id:      int,
    current_business: Business = Depends(get_current_business),
    db:               Session  = Depends(get_db),
):
    """Delete a document and its extracted values."""
    doc = _get_doc_or_404(db, document_id, current_business.id)

    # Delete physical file
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete extracted values and history
    db.query(ExtractedValue).filter(ExtractedValue.document_id == doc.id).delete()
    db.query(DocumentHistory).filter(DocumentHistory.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()

    return {"message": f"Document {document_id} deleted successfully."}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_doc_or_404(db: Session, document_id: int, business_id: int) -> Document:
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == business_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return doc


def _check_file_exists(doc: Document):
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server.")


def _add_history(db: Session, document_id: int, event: str, message: str):
    h = DocumentHistory(document_id=document_id, event=event, message=message)
    db.add(h)
    db.commit()


def _trigger_extraction(db: Session, doc: Document):
    """
    Placeholder for AI extraction.
    Replace this with your actual AI/OCR call (e.g. AWS Textract, Google Vision, Claude API).
    For now it marks the document as processed with dummy values.
    """
    try:
        # ── Simulated extraction result ───────────────────────────────────────
        dummy_values = [
            ExtractedValue(document_id=doc.id, field_name="total_revenue",    value="5200000.00", confidence=0.95, page=1),
            ExtractedValue(document_id=doc.id, field_name="total_expenses",   value="3100000.00", confidence=0.93, page=1),
            ExtractedValue(document_id=doc.id, field_name="accounting_profit",value="2100000.00", confidence=0.91, page=2),
            ExtractedValue(document_id=doc.id, field_name="tax_paid",         value="420000.00",  confidence=0.88, page=3),
        ]
        for v in dummy_values:
            db.add(v)

        doc.status       = "processed"
        doc.processed_at = datetime.utcnow()
        db.commit()

        h = DocumentHistory(document_id=doc.id, event="processed",
                            message="AI extraction completed successfully.")
        db.add(h)
        db.commit()

    except Exception as e:
        doc.status           = "failed"
        doc.extraction_notes = str(e)
        db.commit()

        h = DocumentHistory(document_id=doc.id, event="failed",
                            message=f"AI extraction failed: {e}")
        db.add(h)
        db.commit()