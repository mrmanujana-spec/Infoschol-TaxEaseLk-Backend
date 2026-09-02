from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# ============================================================
# SHARED ENUMS
# ============================================================

class IssueSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"
    error = "error"


class IssueStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    ignored = "ignored"


# ============================================================
# AUDITOR ENUMS
# ============================================================

class CITStatus(str, Enum):
    draft = "draft"
    under_review = "under_review"
    ready_for_auditor = "ready_for_auditor"
    approved = "approved"


class ReviewStatus(str, Enum):
    not_started = "not_started"
    pending = "pending"
    in_progress = "in_progress"
    waiting_for_company = "waiting_for_company"
    ready_for_approval = "ready_for_approval"
    completed = "completed"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AuditUserType(str, Enum):
    auditor = "Auditor"
    ai_system = "AI System"
    company_user = "Company User"


class UserRoleEnum(str, Enum):
    owner = "owner"
    admin = "admin"
    accountant = "accountant"
    viewer = "viewer"


class UserStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"
    invited = "invited"


class SubmissionStatus(str, Enum):
    draft = "draft"
    validating = "validating"
    ready = "ready"
    submitted = "submitted"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"
    expired = "expired"


# ============================================================
# BUSINESS SCHEMAS
# ============================================================

class BusinessBase(BaseModel):
    company_name: str
    registration_number: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    vat_registered: bool = False
    vat_number: Optional[str] = None
    auditor_name: Optional[str] = None
    auditor_status: Optional[str] = None


class BusinessResponse(BusinessBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessUpdate(BaseModel):
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    vat_registered: Optional[bool] = None
    vat_number: Optional[str] = None
    auditor_name: Optional[str] = None
    auditor_status: Optional[str] = None


class BusinessProfile(BaseModel):
    id: int
    email: EmailStr
    company_name: str
    registration_number: Optional[str] = None
    tin: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    incorporation_date: Optional[datetime] = None
    auditor_status: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# FINANCIAL YEAR SCHEMAS
# ============================================================

class FinancialYearResponse(BaseModel):
    id: int
    year_label: str
    start_date: datetime
    end_date: datetime
    is_current: bool
    accounting_profit: float
    taxable_income: float
    estimated_cit: float
    tax_rate: float

    class Config:
        from_attributes = True


class FinancialYearOut(BaseModel):
    id: int
    business_id: int
    year_label: str
    start_date: datetime
    end_date: datetime
    accounting_profit: float = 0.0
    taxable_income: float = 0.0
    estimated_cit: float = 0.0
    is_current: bool = False
    is_filed: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# DASHBOARD SCHEMAS
# ============================================================

class DocumentProgress(BaseModel):
    uploaded: int
    total: int
    label: Optional[str] = None
    percent: Optional[float] = None
    percentage: Optional[float] = None

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    progress: float
    documents: DocumentProgress
    accounting_profit: float
    taxable_income: float
    estimated_cit_liability: float
    auditor_status: str
    unresolved_action_items: int


class DashboardOut(BaseModel):
    progress: int
    documents: DocumentProgress
    accounting_profit: float = 0.0
    taxable_income: float = 0.0
    estimated_cit: float = 0.0
    auditor_status: Optional[str] = None
    requires_attention: int = 0

    class Config:
        from_attributes = True


# ============================================================
# ACTION REQUIRED SCHEMAS
# ============================================================

class ActionItemSummary(BaseModel):
    id: int
    title: str
    severity: IssueSeverity
    category: Optional[str]
    due_date: Optional[datetime]
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ActionItemDetail(ActionItemSummary):
    description: Optional[str]


class ActionRequiredOut(BaseModel):
    id: int
    business_id: int
    title: str
    description: str
    severity: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    action_url: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActionRequiredList(BaseModel):
    total: int
    issues: List[ActionRequiredOut]


# ============================================================
# REPORT SCHEMAS
# ============================================================

class ReportListItem(BaseModel):
    id: str
    name: str
    description: str
    available: bool


class ReportItem(BaseModel):
    id: str
    name: str
    description: str
    url: str


class ReportsListOut(BaseModel):
    reports: List[ReportItem]


class ReportSummaryResponse(BaseModel):
    financial_year: str
    accounting_profit: float
    taxable_income: float
    tax_rate: float
    estimated_cit: float
    documents_uploaded: int
    documents_total: int
    auditor_status: str
    generated_at: datetime


class SummaryReportOut(BaseModel):
    financial_year: str
    accounting_profit: float = 0.0
    taxable_income: float = 0.0
    estimated_cit: float = 0.0
    effective_tax_rate: float = 0.0
    documents_filed: int = 0
    documents_total: int = 0
    auditor_status: Optional[str] = None
    generated_at: Optional[datetime] = None


# ============================================================
# NOTIFICATION SCHEMAS — BUSINESS
# ============================================================

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    notification_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationOut(BaseModel):
    id: int
    business_id: int
    title: str
    message: str
    is_read: bool = False
    notif_type: Optional[str] = None
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationsListOut(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationOut]


class UnreadCountOut(BaseModel):
    unread_count: int


# ============================================================
# SEARCH SCHEMAS
# ============================================================

class SearchResultItem(BaseModel):
    type: str
    id: int
    title: str
    description: Optional[str]
    url: str


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int


class SearchResult(SearchResultItem):
    pass


class SearchOut(SearchResponse):
    pass


# ============================================================
# AUDITOR PROFILE SCHEMAS
# ============================================================

class AuditorProfileOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    photo_url: Optional[str] = None


class AuditorProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None


# ============================================================
# FIRM SCHEMAS
# ============================================================

class FirmOut(BaseModel):
    id: str
    firm_name: str
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None


class FirmUpdate(BaseModel):
    firm_name: Optional[str] = None
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None


# ============================================================
# AUDITOR NOTIFICATION PREFERENCES
# ============================================================

class NotificationPreferencesOut(BaseModel):
    new_submissions: bool = True
    business_responses: bool = True
    document_uploads: bool = True
    messages: bool = True
    review_reminders: bool = True


class NotificationPreferencesUpdate(BaseModel):
    new_submissions: Optional[bool] = None
    business_responses: Optional[bool] = None
    document_uploads: Optional[bool] = None
    messages: Optional[bool] = None
    review_reminders: Optional[bool] = None


# ============================================================
# SUBSCRIPTION SCHEMAS
# ============================================================

class SubscriptionOut(BaseModel):
    plan_name: str
    price_per_month: float
    status: str
    features: List[str] = []
    next_billing_date: Optional[date] = None


class ManageSubscriptionResponse(BaseModel):
    portal_url: str


# ============================================================
# SECURITY SCHEMAS
# ============================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TwoFactorStatusOut(BaseModel):
    enabled: bool
    factor_ids: List[str] = []


class MessageOut(BaseModel):
    message: str


# ============================================================
# COMPANY SCHEMAS (AUDITOR SIDE)
# ============================================================

class CompanyCreate(BaseModel):
    name: str
    tin: str = Field(..., examples=["TIN134578291"])
    financial_year: str = Field(..., examples=["2025/26"])
    due_date: Optional[date] = None
    risk_level: Optional[RiskLevel] = None


class CompanyUpdate(BaseModel):
    cit_status: Optional[CITStatus] = None
    review_status: Optional[ReviewStatus] = None
    risk_level: Optional[RiskLevel] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[date] = None


class CompanyOut(BaseModel):
    id: str
    name: str
    tin: str
    financial_year: str
    cit_status: CITStatus
    review_status: ReviewStatus
    risk_level: Optional[RiskLevel] = None
    progress_percent: int = 0
    due_date: Optional[date] = None
    critical_issues_count: int = 0
    warnings_count: int = 0
    created_at: datetime


class CompanyImportRequest(BaseModel):
    companies: List[CompanyCreate]


# ============================================================
# ISSUE SCHEMAS (AUDITOR SIDE)
# ============================================================

class IssueOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    title: str
    amount: Optional[float] = None
    severity: IssueSeverity
    status: IssueStatus
    source: Optional[str] = None
    created_at: datetime


class IssueResolve(BaseModel):
    resolution_note: Optional[str] = None


class IssueSummaryOut(BaseModel):
    critical: int = 0
    warnings: int = 0
    information: int = 0
    resolved: int = 0


# ============================================================
# AUDIT LOG SCHEMAS
# ============================================================

class AuditLogOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    user_type: AuditUserType
    user_name: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime


# ============================================================
# AUDITOR DASHBOARD SCHEMAS
# ============================================================

class DashboardSummaryOut(BaseModel):
    companies_assigned: int = 0
    pending_reviews: int = 0
    critical_issues: int = 0
    completed: int = 0


class WorkloadOut(BaseModel):
    pending: int = 0
    in_progress: int = 0
    waiting_for_company: int = 0
    ready_for_approval: int = 0
    completed: int = 0


class PriorityReviewOut(BaseModel):
    company_id: str
    company_name: str
    priority_label: str
    critical_issues_count: int = 0
    warnings_count: int = 0
    due_date: Optional[date] = None
    progress_percent: int = 0


# ============================================================
# AUDITOR INVITATION SCHEMAS
# ============================================================

class AuditorInvitationCreate(BaseModel):
    auditor_name: str
    auditor_email: EmailStr
    auditor_firm: Optional[str] = None
    message: Optional[str] = None
    financial_year_id: Optional[int] = None


class AuditorInvitationOut(BaseModel):
    id: int
    business_id: int
    financial_year_id: Optional[int] = None
    auditor_name: str
    auditor_email: str
    auditor_firm: Optional[str] = None
    message: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditorInvitationList(BaseModel):
    total: int
    invitations: List[AuditorInvitationOut]


# ============================================================
# AUDITOR SUBMISSION SCHEMAS
# ============================================================

class CreateSubmissionRequest(BaseModel):
    financial_year_id: Optional[int] = None
    title: Optional[str] = None
    notes: Optional[str] = None


class AuditorSubmissionOut(BaseModel):
    id: int
    business_id: int
    financial_year_id: Optional[int] = None
    title: str
    status: str
    notes: Optional[str] = None
    package_path: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditorSubmissionList(BaseModel):
    total: int
    submissions: List[AuditorSubmissionOut]
