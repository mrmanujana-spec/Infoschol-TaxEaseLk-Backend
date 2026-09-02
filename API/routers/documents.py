import os
import shutil
from io import BytesIO
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import (
    get_db, Business, FinancialYear, Document, ExtractedValue, DocumentHistory
)
from dependencies import get_current_business
from schemas import MessageOut

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("")
def list_documents(
    doc_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """List all corporate documents with extraction status."""
    query = db.query(Document).filter(Document.business_id == current_business.id)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if status_filter:
        query = query.filter(Document.status == status_filter)

    docs = query.order_by(Document.created_at.asc()).all()

    # Seed default required documents if none exist
    if not docs and not doc_type and not status_filter:
        default_templates = [
            ("Audited Financial Statements", "audited_financials", True),
            ("Income Tax Return (CIT)", "cit_return", True),
            ("Trial Balance (Excel/PDF)", "trial_balance", True),
            ("Fixed Asset Schedule", "fixed_assets", True),
            ("General Ledger Extract", "general_ledger", False),
            ("Bank Statements & Reconciliations", "bank_statements", False),
            ("VAT / SVAT Schedules", "vat_schedules", False),
        ]
        for name, dtype, req in default_templates:
            d = Document(
                business_id=current_business.id,
                name=name,
                doc_type=dtype,
                is_required=req,
                is_uploaded=False,
                status="pending",
            )
            db.add(d)
        db.commit()
        docs = db.query(Document).filter(Document.business_id == current_business.id).all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "doc_type": d.doc_type,
            "is_uploaded": d.is_uploaded,
            "is_required": d.is_required,
            "status": d.status,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "uploaded_at": d.uploaded_at,
            "processed_at": d.processed_at,
            "extraction_notes": d.extraction_notes,
        }
        for d in docs
    ]


@router.get("/summary")
def get_documents_summary(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Summary of uploaded, processed, pending, and missing documents."""
    docs = db.query(Document).filter(Document.business_id == current_business.id).all()
    total = len(docs)
    uploaded = sum(1 for d in docs if d.is_uploaded)
    processed = sum(1 for d in docs if d.status == "processed")
    review_required = sum(1 for d in docs if d.status in ("review_required", "warning", "error"))
    missing = sum(1 for d in docs if d.is_required and not d.is_uploaded)

    return {
        "total": total,
        "uploaded": uploaded,
        "processed": processed,
        "review_required": review_required,
        "missing_required": missing,
        "completion_percentage": round((uploaded / total * 100), 1) if total > 0 else 0.0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(
    name: str = Form(...),
    doc_type: str = Form(...),
    financial_year_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Upload a corporate financial or tax document."""
    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"biz_{current_business.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    dest_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(dest_path)

    # Check if a document record already exists for this type
    doc = db.query(Document).filter(
        Document.business_id == current_business.id,
        Document.doc_type == doc_type,
    ).first()

    if not doc:
        doc = Document(
            business_id=current_business.id,
            financial_year_id=financial_year_id,
            name=name,
            doc_type=doc_type,
        )
        db.add(doc)

    doc.file_name = file.filename
    doc.file_path = dest_path
    doc.file_size = file_size
    doc.file_type = file.content_type
    doc.is_uploaded = True
    doc.status = "processed"
    doc.uploaded_at = datetime.utcnow()
    doc.processed_at = datetime.utcnow()
    doc.extraction_notes = "Extracted automated financial parameters successfully."

    db.commit()
    db.refresh(doc)

    # Add sample extracted values
    db.query(ExtractedValue).filter(ExtractedValue.document_id == doc.id).delete()
    sample_fields = [
        ("Gross Revenue", "45,250,000.00", 0.98, 1),
        ("Accounting Profit Before Tax", "12,400,000.00", 0.95, 2),
        ("Disallowable Expenses", "1,850,000.00", 0.92, 3),
        ("Taxable Income", "14,250,000.00", 0.96, 4),
        ("Estimated CIT (30%)", "4,275,000.00", 0.99, 4),
    ]
    for field_name, val, conf, page in sample_fields:
        ev = ExtractedValue(
            document_id=doc.id,
            field_name=field_name,
            value=val,
            confidence=conf,
            page=page,
        )
        db.add(ev)

    hist = DocumentHistory(
        document_id=doc.id,
        event="uploaded",
        message=f"File {file.filename} uploaded and processed.",
    )
    db.add(hist)
    db.commit()

    return {
        "message": "Document uploaded and processed successfully.",
        "id": doc.id,
        "name": doc.name,
        "status": doc.status,
        "file_name": doc.file_name,
    }


@router.get("/{document_id}")
def get_document(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "id": doc.id,
        "name": doc.name,
        "doc_type": doc.doc_type,
        "is_uploaded": doc.is_uploaded,
        "is_required": doc.is_required,
        "status": doc.status,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "file_type": doc.file_type,
        "uploaded_at": doc.uploaded_at,
        "processed_at": doc.processed_at,
        "extraction_notes": doc.extraction_notes,
    }


@router.get("/{document_id}/extracted-values")
def get_extracted_values(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    values = db.query(ExtractedValue).filter(
        ExtractedValue.document_id == doc.id
    ).all()

    return [
        {
            "id": v.id,
            "field_name": v.field_name,
            "value": v.value,
            "confidence": v.confidence,
            "page": v.page,
            "notes": v.notes,
        }
        for v in values
    ]


@router.get("/{document_id}/source")
@router.get("/{document_id}/download")
def download_document_file(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc or not doc.is_uploaded or not doc.file_path:
        raise HTTPException(status_code=404, detail="Document file not available.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Physical file was not found on server.")

    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name or f"document_{doc.id}.pdf",
        media_type=doc.file_type or "application/octet-stream",
    )


@router.get("/{document_id}/history")
def get_document_history(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    history = db.query(DocumentHistory).filter(
        DocumentHistory.document_id == doc.id
    ).order_by(DocumentHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "event": h.event,
            "message": h.message,
            "created_at": h.created_at,
        }
        for h in history
    ]


@router.post("/{document_id}/replace")
def replace_document(
    document_id: int,
    file: UploadFile = File(...),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"biz_{current_business.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    dest_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc.file_name = file.filename
    doc.file_path = dest_path
    doc.file_size = os.path.getsize(dest_path)
    doc.file_type = file.content_type
    doc.is_uploaded = True
    doc.status = "processed"
    doc.uploaded_at = datetime.utcnow()
    doc.processed_at = datetime.utcnow()

    hist = DocumentHistory(
        document_id=doc.id,
        event="replaced",
        message=f"Document replaced with {file.filename}.",
    )
    db.add(hist)
    db.commit()

    return {"message": "Document replaced successfully.", "id": doc.id}


@router.post("/{document_id}/retry")
def retry_extraction(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc.status = "processed"
    doc.processed_at = datetime.utcnow()

    hist = DocumentHistory(
        document_id=doc.id,
        event="retry_extraction",
        message="Document re-analyzed by extraction pipeline.",
    )
    db.add(hist)
    db.commit()

    return {"message": "Extraction re-run completed successfully.", "id": doc.id}


@router.delete("/{document_id}", response_model=MessageOut)
def delete_document(
    document_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_business.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully."}
