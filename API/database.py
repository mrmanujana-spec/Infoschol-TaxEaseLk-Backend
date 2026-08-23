import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON
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

class SubmissionStatusEnum(str, enum.Enum):
    draft      = "draft"
    validating = "validating"
    ready      = "ready"
    submitted  = "submitted"
    in_review  = "in_review"
    approved   = "approved"
    rejected   = "rejected"

class InvitationStatusEnum(str, enum.Enum):
    pending   = "pending"
    accepted  = "accepted"
    declined  = "declined"
    cancelled = "cancelled"
    expired   = "expired"

class ReviewIssueStatusEnum(str, enum.Enum):
    open      = "open"
    responded = "responded"
    resolved  = "resolved"

class UserRoleEnum(str, enum.Enum):
    owner     = "owner"
    admin     = "admin"
    accountant= "accountant"
    viewer    = "viewer"

class UserStatusEnum(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    invited  = "invited"


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
    address             = Column(Text,   nullable=True)
    industry            = Column(String, nullable=True)
    incorporation_date  = Column(DateTime, nullable=True)
    auditor_status      = Column(Enum(AuditorStatusEnum), default=AuditorStatusEnum.not_required)
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    financial_years      = relationship("FinancialYear",      back_populates="business")
    documents            = relationship("Document",           back_populates="business")
    issues               = relationship("ActionRequired",     back_populates="business")
    notifications        = relationship("Notification",       back_populates="business")
    submissions          = relationship("AuditorSubmission",  back_populates="business")
    invitations          = relationship("AuditorInvitation",  back_populates="business")
    users                = relationship("CompanyUser",        back_populates="business")
    security_settings    = relationship("SecuritySetting",    back_populates="business", uselist=False)
    notification_prefs   = relationship("NotificationPreference", back_populates="business", uselist=False)
    audit_logs           = relationship("AuditLog",           back_populates="business")
    sessions             = relationship("UserSession",        back_populates="business")


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

    business  = relationship("Business",     back_populates="financial_years")
    documents = relationship("Document",     back_populates="financial_year")


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

    business         = relationship("Business",      back_populates="documents")
    financial_year   = relationship("FinancialYear", back_populates="documents")
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


class AuditorSubmission(Base):
    __tablename__ = "auditor_submissions"

    id                = Column(Integer, primary_key=True, index=True)
    business_id       = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id"), nullable=True)
    title             = Column(String, nullable=False)
    status            = Column(Enum(SubmissionStatusEnum), default=SubmissionStatusEnum.draft)
    notes             = Column(Text,   nullable=True)
    package_path      = Column(String, nullable=True)
    submitted_at      = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="submissions")
    history  = relationship("SubmissionHistory", back_populates="submission", cascade="all, delete-orphan")


class SubmissionHistory(Base):
    __tablename__ = "submission_history"

    id            = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("auditor_submissions.id"), nullable=False)
    event         = Column(String, nullable=False)
    message       = Column(Text,   nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    submission = relationship("AuditorSubmission", back_populates="history")


class AuditorInvitation(Base):
    __tablename__ = "auditor_invitations"

    id                = Column(Integer, primary_key=True, index=True)
    business_id       = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id"), nullable=True)
    auditor_name      = Column(String, nullable=False)
    auditor_email     = Column(String, nullable=False)
    auditor_firm      = Column(String, nullable=True)
    message           = Column(Text,   nullable=True)
    status            = Column(Enum(InvitationStatusEnum), default=InvitationStatusEnum.pending)
    sent_at           = Column(DateTime, default=datetime.utcnow)
    accepted_at       = Column(DateTime, nullable=True)
    cancelled_at      = Column(DateTime, nullable=True)
    expires_at        = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="invitations")


class AuditorReview(Base):
    __tablename__ = "auditor_reviews"

    id            = Column(Integer, primary_key=True, index=True)
    business_id   = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("auditor_submissions.id"), nullable=True)
    status        = Column(String, default="in_review")
    notes         = Column(Text,   nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    issues = relationship("ReviewIssue", back_populates="review", cascade="all, delete-orphan")


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id           = Column(Integer, primary_key=True, index=True)
    review_id    = Column(Integer, ForeignKey("auditor_reviews.id"), nullable=False)
    title        = Column(String, nullable=False)
    description  = Column(Text,   nullable=False)
    status       = Column(Enum(ReviewIssueStatusEnum), default=ReviewIssueStatusEnum.open)
    response     = Column(Text,   nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    review      = relationship("AuditorReview", back_populates="issues")
    attachments = relationship("ReviewIssueAttachment", back_populates="issue", cascade="all, delete-orphan")


class ReviewIssueAttachment(Base):
    __tablename__ = "review_issue_attachments"

    id          = Column(Integer, primary_key=True, index=True)
    issue_id    = Column(Integer, ForeignKey("review_issues.id"), nullable=False)
    file_name   = Column(String, nullable=False)
    file_path   = Column(String, nullable=False)
    file_size   = Column(Integer, nullable=True)
    file_type   = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("ReviewIssue", back_populates="attachments")


class CompanyUser(Base):
    __tablename__ = "company_users"

    id          = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name        = Column(String, nullable=False)
    email       = Column(String, nullable=False)
    role        = Column(Enum(UserRoleEnum), default=UserRoleEnum.viewer)
    status      = Column(Enum(UserStatusEnum), default=UserStatusEnum.invited)
    permissions = Column(Text, nullable=True)  # JSON string
    invited_at  = Column(DateTime, default=datetime.utcnow)
    joined_at   = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="users")


class SecuritySetting(Base):
    __tablename__ = "security_settings"

    id                    = Column(Integer, primary_key=True, index=True)
    business_id           = Column(Integer, ForeignKey("businesses.id"), unique=True, nullable=False)
    two_fa_enabled        = Column(Boolean, default=False)
    two_fa_secret         = Column(String, nullable=True)
    two_fa_method         = Column(String, default="email")  # email, authenticator
    session_timeout_mins  = Column(Integer, default=60)
    ip_whitelist          = Column(Text, nullable=True)  # JSON list
    login_notifications   = Column(Boolean, default=True)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="security_settings")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id          = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    device      = Column(String, nullable=True)
    browser     = Column(String, nullable=True)
    ip_address  = Column(String, nullable=True)
    location    = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_seen   = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="sessions")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id                     = Column(Integer, primary_key=True, index=True)
    business_id            = Column(Integer, ForeignKey("businesses.id"), unique=True, nullable=False)
    email_notifications    = Column(Boolean, default=True)
    sms_notifications      = Column(Boolean, default=False)
    filing_deadlines       = Column(Boolean, default=True)
    document_processed     = Column(Boolean, default=True)
    auditor_updates        = Column(Boolean, default=True)
    system_alerts          = Column(Boolean, default=True)
    weekly_summary         = Column(Boolean, default=True)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="notification_prefs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    user_email  = Column(String, nullable=True)
    action      = Column(String, nullable=False)
    resource    = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    details     = Column(Text,   nullable=True)
    ip_address  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="audit_logs")


# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)