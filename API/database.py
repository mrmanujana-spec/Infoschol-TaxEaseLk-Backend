import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = "sqlite:///./taxeaselk.db"
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────

class AuditorStatusEnum(str, enum.Enum):
    not_required = "not_required"
    pending      = "pending"
    in_review    = "in_review"
    approved     = "approved"
    rejected     = "rejected"

class IssueSeverityEnum(str, enum.Enum):
    error   = "error"
    warning = "warning"
    info    = "info"

class IssueStatusEnum(str, enum.Enum):
    open     = "open"
    resolved = "resolved"
    ignored  = "ignored"

class DocumentStatusEnum(str, enum.Enum):
    pending          = "pending"
    processing       = "processing"
    processed        = "processed"
    review_required  = "review_required"
    failed           = "failed"


# ─── Models ──────────────────────────────────────────────────────────────────

class Business(Base):
    __tablename__ = "businesses"

    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String, unique=True, index=True, nullable=False)
    hashed_password     = Column(String, nullable=False)
    company_name        = Column(String, nullable=False)
    registration_number = Column(String, unique=True, nullable=True)
    tin                 = Column(String, unique=True, nullable=True)
    phone               = Column(String, nullable=True)
    address             = Column(Text, nullable=True)
    industry            = Column(String, nullable=True)
    incorporation_date  = Column(DateTime, nullable=True)
    auditor_status      = Column(Enum(AuditorStatusEnum), default=AuditorStatusEnum.not_required)
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    financial_years = relationship("FinancialYear",  back_populates="business")
    documents       = relationship("Document",       back_populates="business")
    issues          = relationship("ActionRequired", back_populates="business")
    notifications   = relationship("Notification",   back_populates="business")


class FinancialYear(Base):
    __tablename__ = "financial_years"

    id                = Column(Integer, primary_key=True, index=True)
    business_id       = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    year_label        = Column(String,  nullable=False)
    start_date        = Column(DateTime, nullable=False)
    end_date          = Column(DateTime, nullable=False)
    accounting_profit = Column(Float, default=0.0)
    taxable_income    = Column(Float, default=0.0)
    estimated_cit     = Column(Float, default=0.0)
    is_current        = Column(Boolean, default=False)
    is_filed          = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    business  = relationship("Business",  back_populates="financial_years")
    documents = relationship("Document",  back_populates="financial_year")


class Document(Base):
    __tablename__ = "documents"

    id                = Column(Integer, primary_key=True, index=True)
    business_id       = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id"), nullable=True)
    name              = Column(String,  nullable=False)
    doc_type          = Column(String,  nullable=False)
    file_path         = Column(String,  nullable=True)
    file_name         = Column(String,  nullable=True)
    file_size         = Column(Integer, nullable=True)
    file_type         = Column(String,  nullable=True)
    is_uploaded       = Column(Boolean, default=False)
    is_required       = Column(Boolean, default=True)
    status            = Column(String,  default="pending")
    extraction_notes  = Column(Text,    nullable=True)
    uploaded_at       = Column(DateTime, nullable=True)
    processed_at      = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)

    business       = relationship("Business",      back_populates="documents")
    financial_year = relationship("FinancialYear", back_populates="documents")
    extracted_values = relationship("ExtractedValue",  back_populates="document", cascade="all, delete-orphan")
    history          = relationship("DocumentHistory", back_populates="document",  cascade="all, delete-orphan")


class ExtractedValue(Base):
    __tablename__ = "extracted_values"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name  = Column(String,  nullable=False)
    value       = Column(String,  nullable=True)
    confidence  = Column(Float,   nullable=True)
    page        = Column(Integer, nullable=True)
    notes       = Column(Text,    nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="extracted_values")


class DocumentHistory(Base):
    __tablename__ = "document_history"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    event       = Column(String, nullable=False)
    message     = Column(Text,   nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="history")


class ActionRequired(Base):
    __tablename__ = "action_required"

    id          = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    title       = Column(String, nullable=False)
    description = Column(Text,   nullable=False)
    severity    = Column(Enum(IssueSeverityEnum), default=IssueSeverityEnum.warning)
    status      = Column(Enum(IssueStatusEnum),   default=IssueStatusEnum.open)
    category    = Column(String, nullable=True)
    action_url  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="issues")


class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    title       = Column(String, nullable=False)
    message     = Column(Text,   nullable=False)
    is_read     = Column(Boolean, default=False)
    notif_type  = Column(String,  nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    read_at     = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="notifications")


# ─── DB Session dependency ────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)