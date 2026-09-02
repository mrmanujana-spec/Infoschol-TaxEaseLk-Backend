"""
TaxEaseLK — Unified Database & Supabase PostgreSQL Connection
Provides Supabase client (service & anon) and SQLAlchemy ORM models.
"""

import os
import enum
from datetime import datetime
from typing import Optional, Generator
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Date, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

load_dotenv()

# ─── Supabase Client Setup ──────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

service_key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
anon_key = SUPABASE_ANON_KEY or SUPABASE_KEY or SUPABASE_SERVICE_KEY

supabase = None
supabase_anon = None

try:
    from supabase import create_client, Client
    if SUPABASE_URL and service_key:
        supabase = create_client(SUPABASE_URL, service_key)
    if SUPABASE_URL and anon_key:
        supabase_anon = create_client(SUPABASE_URL, anon_key)
except Exception as e:
    print(f"Supabase client initialization notice: {e}")

# Fallback wrapper if supabase client is None to prevent startup crashes
class SupabaseDummyClient:
    def __getattr__(self, name):
        raise RuntimeError(
            f"Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file."
        )

if supabase is None:
    supabase = SupabaseDummyClient()
if supabase_anon is None:
    supabase_anon = SupabaseDummyClient()


# ─── SQLAlchemy Engine & Session Setup ──────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Default fallback to SQLite for local development when PostgreSQL URL is not provided
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./taxeaselk.db"

# Ensure postgresql:// prefix is used instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────

class AuditorStatusEnum(str, enum.Enum):
    not_required = "not_required"
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


class IssueSeverityEnum(str, enum.Enum):
    error = "error"
    warning = "warning"
    info = "info"
    critical = "critical"


class IssueStatusEnum(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    ignored = "ignored"


class SubmissionStatusEnum(str, enum.Enum):
    draft = "draft"
    validating = "validating"
    ready = "ready"
    submitted = "submitted"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


class InvitationStatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"
    expired = "expired"


class ReviewIssueStatusEnum(str, enum.Enum):
    open = "open"
    responded = "responded"
    resolved = "resolved"


class UserRoleEnum(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    accountant = "accountant"
    viewer = "viewer"


class UserStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    invited = "invited"


class CITStatusEnum(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    ready_for_auditor = "ready_for_auditor"
    approved = "approved"


class ReviewStatusEnum(str, enum.Enum):
    not_started = "not_started"
    pending = "pending"
    in_progress = "in_progress"
    waiting_for_company = "waiting_for_company"
    ready_for_approval = "ready_for_approval"
    completed = "completed"


class RiskLevelEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AuditUserTypeEnum(str, enum.Enum):
    auditor = "Auditor"
    ai_system = "AI System"
    company_user = "Company User"


# ─── SQLAlchemy Models ───────────────────────────────────────────────────────

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True, default="")
    company_name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=True)
    tin = Column(String(100), unique=True, nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    incorporation_date = Column(DateTime, nullable=True)
    vat_registered = Column(Boolean, default=False)
    vat_number = Column(String(100), nullable=True)
    auditor_name = Column(String(255), nullable=True)
    auditor_status = Column(SAEnum(AuditorStatusEnum), default=AuditorStatusEnum.not_required)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    financial_years = relationship("FinancialYear", back_populates="business", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="business", cascade="all, delete-orphan")
    issues = relationship("ActionRequired", back_populates="business", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="business", cascade="all, delete-orphan")
    submissions = relationship("AuditorSubmission", back_populates="business", cascade="all, delete-orphan")
    invitations = relationship("AuditorInvitation", back_populates="business", cascade="all, delete-orphan")
    reviews = relationship("AuditorReview", back_populates="business", cascade="all, delete-orphan")
    users = relationship("CompanyUser", back_populates="business", cascade="all, delete-orphan")
    security_settings = relationship("SecuritySetting", back_populates="business", uselist=False, cascade="all, delete-orphan")
    notification_prefs = relationship("NotificationPreference", back_populates="business", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="business", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="business", cascade="all, delete-orphan")


class FinancialYear(Base):
    __tablename__ = "financial_years"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    year_label = Column(String(50), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    accounting_profit = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    estimated_cit = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.30)
    is_current = Column(Boolean, default=False)
    is_filed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="financial_years")
    documents = relationship("Document", back_populates="financial_year")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    doc_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    is_uploaded = Column(Boolean, default=False)
    is_required = Column(Boolean, default=True)
    status = Column(String(50), default="pending")
    extraction_notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="documents")
    financial_year = relationship("FinancialYear", back_populates="documents")
    extracted_values = relationship("ExtractedValue", back_populates="document", cascade="all, delete-orphan")
    history = relationship("DocumentHistory", back_populates="document", cascade="all, delete-orphan")


class ExtractedValue(Base):
    __tablename__ = "extracted_values"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    value = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    page = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="extracted_values")


class DocumentHistory(Base):
    __tablename__ = "document_history"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    event = Column(String(100), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="history")


class ActionRequired(Base):
    __tablename__ = "action_required"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SAEnum(IssueSeverityEnum), default=IssueSeverityEnum.warning)
    status = Column(SAEnum(IssueStatusEnum), default=IssueStatusEnum.open)
    category = Column(String(100), nullable=True)
    action_url = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="issues")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    notif_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="notifications")


class AuditorSubmission(Base):
    __tablename__ = "auditor_submissions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(SubmissionStatusEnum), default=SubmissionStatusEnum.draft)
    notes = Column(Text, nullable=True)
    package_path = Column(String(500), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="submissions")
    history = relationship("SubmissionHistory", back_populates="submission", cascade="all, delete-orphan")


class SubmissionHistory(Base):
    __tablename__ = "submission_history"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("auditor_submissions.id", ondelete="CASCADE"), nullable=False)
    event = Column(String(100), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("AuditorSubmission", back_populates="history")


class AuditorInvitation(Base):
    __tablename__ = "auditor_invitations"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="SET NULL"), nullable=True)
    auditor_name = Column(String(255), nullable=False)
    auditor_email = Column(String(255), nullable=False)
    auditor_firm = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(SAEnum(InvitationStatusEnum), default=InvitationStatusEnum.pending)
    sent_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="invitations")


class AuditorReview(Base):
    __tablename__ = "auditor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(Integer, ForeignKey("auditor_submissions.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="in_review")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="reviews")
    issues = relationship("ReviewIssue", back_populates="review", cascade="all, delete-orphan")


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("auditor_reviews.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(ReviewIssueStatusEnum), default=ReviewIssueStatusEnum.open)
    response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("AuditorReview", back_populates="issues")
    attachments = relationship("ReviewIssueAttachment", back_populates="issue", cascade="all, delete-orphan")


class ReviewIssueAttachment(Base):
    __tablename__ = "review_issue_attachments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("review_issues.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("ReviewIssue", back_populates="attachments")


class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRoleEnum), default=UserRoleEnum.viewer)
    status = Column(SAEnum(UserStatusEnum), default=UserStatusEnum.invited)
    permissions = Column(Text, nullable=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="users")


class SecuritySetting(Base):
    __tablename__ = "security_settings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False)
    two_fa_enabled = Column(Boolean, default=False)
    two_fa_secret = Column(String(255), nullable=True)
    two_fa_method = Column(String(50), default="email")
    session_timeout_mins = Column(Integer, default=60)
    ip_whitelist = Column(Text, nullable=True)
    login_notifications = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="security_settings")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    device = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    ip_address = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="sessions")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    filing_deadlines = Column(Boolean, default=True)
    document_processed = Column(Boolean, default=True)
    auditor_updates = Column(Boolean, default=True)
    system_alerts = Column(Boolean, default=True)
    weekly_summary = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="notification_prefs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="audit_logs")


# ─── DB Helpers ──────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Yield a database session and safely close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    print("Database tables verified.")
