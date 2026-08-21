from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


# ---------- Enums (these are the exact status labels/tabs from your UI) ----------

class CITStatus(str, Enum):
    draft = "draft"
    under_review = "under_review"
    ready_for_auditor = "ready_for_auditor"
    approved = "approved"


class ReviewStatus(str, Enum):
    not_started = "not_started"          # "Not Started" (Sunrise Hotels)
    pending = "pending"                  # "Pending" (Green Valley)
    in_progress = "in_progress"          # "In Progress"
    waiting_for_company = "waiting_for_company"  # "Waiting for Company"
    ready_for_approval = "ready_for_approval"    # "Ready for Approval"
    completed = "completed"              # "Completed" / "Approved"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class IssueSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class IssueStatus(str, Enum):
    open = "open"
    resolved = "resolved"


class AuditUserType(str, Enum):
    auditor = "Auditor"
    ai_system = "AI System"
    company_user = "Company User"


# ---------- Auditor profile (Settings > Profile tab) ----------
# Fields exactly as shown: Full Name, Email Address, Phone Number,
# Designation, photo. (Earlier "License No." / "Organization" fields
# don't appear on this version of the screen -- removed. "Organization"
# now looks like it belongs to the separate "Firm" tab instead.)

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


# ---------- Firm (Settings > Firm tab) ----------
# Fields exactly as shown: Firm Name, Registration No., Address Line 1,
# Address Line 2, Contact Number, Email.
# Modeled as its own table (not just fields on the auditor) since a firm
# can have more than one auditor in it -- tell me if that's wrong.

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


# ---------- Notifications (Settings > Notifications tab) ----------
# One toggle per row shown on screen. Per-auditor, not per-firm.

class NotificationPreferencesOut(BaseModel):
    new_submissions: bool
    business_responses: bool
    document_uploads: bool
    messages: bool
    review_reminders: bool


class NotificationPreferencesUpdate(BaseModel):
    new_submissions: Optional[bool] = None
    business_responses: Optional[bool] = None
    document_uploads: Optional[bool] = None
    messages: Optional[bool] = None
    review_reminders: Optional[bool] = None


# ---------- Subscription (Settings > Subscription tab) ----------
# The plan/price/feature list is read-only display data (set by you, the
# platform owner, not editable by the auditor) -- only "Manage Subscription"
# is an action, and that action should hand off to your payment provider's
# billing portal rather than editing rows directly here.

class SubscriptionOut(BaseModel):
    plan_name: str
    price_per_month: float
    status: str  # "active" | "past_due" | "canceled"
    features: List[str]
    next_billing_date: Optional[date] = None


class ManageSubscriptionResponse(BaseModel):
    portal_url: str


# ---------- Security (Settings > Security tab) ----------

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TwoFactorStatusOut(BaseModel):
    enabled: bool
    factor_ids: List[str] = []


class MessageOut(BaseModel):
    message: str


# ---------- Companies (Companies screen + Review Queue screen) ----------

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
    risk_level: Optional[RiskLevel]
    progress_percent: int
    due_date: Optional[date]
    critical_issues_count: int
    warnings_count: int
    created_at: datetime


class CompanyImportRequest(BaseModel):
    companies: List[CompanyCreate]


# ---------- Issues (Issues screen) ----------

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
    critical: int
    warnings: int
    information: int
    resolved: int


# ---------- Audit Log (Audit Log screen) ----------

class AuditLogOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    user_type: AuditUserType
    user_name: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime


# ---------- Dashboard ----------

class DashboardSummaryOut(BaseModel):
    companies_assigned: int
    pending_reviews: int
    critical_issues: int
    completed: int


class WorkloadOut(BaseModel):
    pending: int
    in_progress: int
    waiting_for_company: int
    ready_for_approval: int
    completed: int


class PriorityReviewOut(BaseModel):
    company_id: str
    company_name: str
    priority_label: str  # "CRITICAL" | "ATTENTION_REQUIRED" | "READY_FOR_APPROVAL"
    critical_issues_count: int
    warnings_count: int
    due_date: Optional[date]
    progress_percent: int
