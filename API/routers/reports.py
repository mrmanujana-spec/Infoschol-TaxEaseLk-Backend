from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from io import BytesIO

from database import get_db, Business, FinancialYear, Document
from dependencies import get_current_business
from schemas import ReportsListOut, ReportItem, SummaryReportOut

router = APIRouter(prefix="/business/reports", tags=["Reports"])


@router.get("", response_model=ReportsListOut)
def list_reports(current_business: Business = Depends(get_current_business)):
    return ReportsListOut(reports=[
        ReportItem(
            id="summary",
            name="Tax & Financial Summary",
            description="Overview of accounting profit, taxable income, and CIT liability.",
            url="/business/reports/summary",
        ),
        ReportItem(
            id="summary_pdf",
            name="Summary Report (PDF)",
            description="Downloadable PDF of the Tax & Financial Summary.",
            url="/business/reports/summary/pdf",
        ),
    ])


@router.get("/summary", response_model=SummaryReportOut)
def get_summary_report(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    bid = current_business.id
    current_fy = db.query(FinancialYear).filter(
        FinancialYear.business_id == bid,
        FinancialYear.is_current == True,
    ).first()

    if not current_fy:
        current_fy = FinancialYear(
            business_id=bid,
            year_label=f"{datetime.utcnow().year - 1}/{datetime.utcnow().year % 100:02d}",
            start_date=datetime(datetime.utcnow().year - 1, 4, 1),
            end_date=datetime(datetime.utcnow().year, 3, 31),
            accounting_profit=12400000.0,
            taxable_income=14250000.0,
            estimated_cit=4275000.0,
            is_current=True,
        )
        db.add(current_fy)
        db.commit()
        db.refresh(current_fy)

    all_docs = db.query(Document).filter(Document.business_id == bid).all()
    uploaded_docs = sum(1 for d in all_docs if d.is_uploaded)
    taxable = current_fy.taxable_income
    cit = current_fy.estimated_cit
    eff_rate = round((cit / taxable * 100), 2) if taxable > 0 else 0.0

    auditor_status_str = (
        current_business.auditor_status.value
        if hasattr(current_business.auditor_status, "value")
        else str(current_business.auditor_status)
    )

    return SummaryReportOut(
        financial_year=current_fy.year_label,
        accounting_profit=current_fy.accounting_profit,
        taxable_income=taxable,
        estimated_cit=cit,
        effective_tax_rate=eff_rate,
        documents_filed=uploaded_docs,
        documents_total=len(all_docs),
        auditor_status=auditor_status_str,
        generated_at=datetime.utcnow(),
    )


@router.get("/summary/pdf")
def get_summary_pdf(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation requires reportlab.")

    bid = current_business.id
    current_fy = db.query(FinancialYear).filter(
        FinancialYear.business_id == bid,
        FinancialYear.is_current == True,
    ).first()

    if not current_fy:
        raise HTTPException(status_code=404, detail="No current financial year found.")

    all_docs = db.query(Document).filter(Document.business_id == bid).all()
    uploaded_docs = sum(1 for d in all_docs if d.is_uploaded)
    taxable = current_fy.taxable_income
    cit = current_fy.estimated_cit
    eff_rate = round((cit / taxable * 100), 2) if taxable > 0 else 0.0

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("TaxEase LK – Tax & Financial Summary", styles["Title"]),
        Paragraph(f"Company: {current_business.company_name}", styles["Heading2"]),
        Paragraph(f"Financial Year: {current_fy.year_label}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 20),
    ]

    status_str = (
        current_business.auditor_status.value.replace("_", " ").title()
        if hasattr(current_business.auditor_status, "value")
        else str(current_business.auditor_status).title()
    )

    table_data = [
        ["Item", "Value (LKR)"],
        ["Accounting Profit", f"{current_fy.accounting_profit:,.2f}"],
        ["Taxable Income", f"{taxable:,.2f}"],
        ["Estimated CIT Liability", f"{cit:,.2f}"],
        ["Effective Tax Rate", f"{eff_rate}%"],
        ["Documents Filed", f"{uploaded_docs} / {len(all_docs)}"],
        ["Auditor Status", status_str],
    ]
    table = Table(table_data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)

    filename = f"TaxEaseLK_Summary_{current_fy.year_label.replace('/', '-')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
