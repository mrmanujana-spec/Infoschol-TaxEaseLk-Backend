# TaxEaseLK Backend API & Platform Architecture

TaxEaseLK is an AI-powered Corporate Tax Document & Auditor Collaboration Platform engineered for Sri Lankan Private Limited (`Pvt Ltd`) companies and Certified Tax Auditors / CA Sri Lanka practitioners.

---

## 🏛️ System Architecture Overview

TaxEaseLK bridges **Corporate Taxpayers (Businesses)** and **Licensed Tax Auditors** through a unified FastAPI application backed by **Supabase & PostgreSQL**:

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      Frontend Clients                       │
 │        (Business Portal UI  &  Auditor Workspace UI)        │
 └──────────────┬───────────────────────────────┬──────────────┘
                │ HTTP Requests                 │ Headers:
                │ (JSON / Multipart)            │ X-Business-Id, X-User-Id
                ▼                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                  FastAPI Application (main.py)              │
 │  - CORS Middleware                                          │
 │  - Authentication & Role Context Providers                  │
 │  - Automated Lifespan Table Provisioning                    │
 └──────────────┬───────────────────────────────┬──────────────┘
                │                               │
        ┌───────┴──────────────┐         ┌──────┴──────────────┐
        ▼                      ▼         ▼                     ▼
 ┌─────────────┐        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │  Business   │        │   Auditor   │ │   Reports   │ │  Security   │
 │   Routers   │        │   Routers   │ │  Engine     │ │  & 2FA      │
 └──────┬──────┘        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
        │                      │               │               │
        └──────────────────────┼───────────────┴───────────────┘
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                Database Layer (database.py)                 │
 │  ┌───────────────────────────────┬────────────────────────┐ │
 │  │      SQLAlchemy ORM           │     Supabase Client    │ │
 │  │   (PostgreSQL / SQLite)       │ (PostgREST, Auth, MFA) │ │
 │  └───────────────────────────────┴────────────────────────┘ │
 └─────────────────────────────┬───────────────────────────────┘
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │               Supabase Cloud / PostgreSQL DB                │
 └─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Modules & How the Web Application Works

### 1. Business Workspace (Corporate Taxpayer)
* **Dashboard (`/business/dashboard`)**: Provides high-level metrics including financial year profit, estimated CIT (Corporate Income Tax at 30%), document completion percentage, auditor status, and pending action items.
* **Document Management (`/documents`)**:
  * Upload, replace, retry, and preview financial statements (Balance Sheet, Income Statement, Trial Balance, Fixed Asset Schedule, VAT returns).
  * Automated financial parameter extraction and field-level confidence scoring.
* **Financial Analytics (`/financials`)**:
  * Structured financial statements (Income Statement, Balance Sheet, Trial Balance, General Ledger, Fixed Asset Tax Depreciation).
  * Extracted value audit history with page references.
* **Auditor Collaboration (`/auditor-submissions` & `/auditor-reviews`)**:
  * Draft submission packages with pre-submission validation.
  * Formal submission to assigned auditor.
  * Respond to review issues with explanations and uploaded attachments.
  * Generate and download downloadable PDF tax filing packages.
* **Auditor Invitations (`/auditor-invitations`)**:
  * Send invitations to external tax auditing firms.
  * Resend or cancel pending invitations.
* **Reports (`/business/reports`)**:
  * Real-time Tax & Financial summary.
  * On-demand PDF generation formatted for IRD/RAMIS filing.
* **Company Settings & Team (`/settings`)**:
  * Company profile & Tax Identification Number (`TIN`).
  * Financial years configuration.
  * Multi-user role-based access control (`owner`, `admin`, `accountant`, `viewer`).
  * Two-Factor Authentication (`2FA`), session management, and immutable audit logs.

### 2. Auditor Workspace (Auditing Practitioner)
* **Auditor Dashboard (`/auditor/dashboard`)**:
  * Workload overview: Pending reviews, In Progress, Waiting for Company, Ready for Approval, Completed.
  * Priority review queues and upcoming statutory deadlines.
  * Live cross-company activity feeds.
* **Company Portfolio (`/auditor/companies`)**:
  * Assigned client companies, CIT statuses, review progress, and risk classification (`low`, `medium`, `high`).
  * Bulk import and company metadata management.
* **Review Queue (`/auditor/review-queue`)**:
  * Streamlined tabbed audit review workflow.
  * Single-click approval of CIT filings and requests for additional client documentation.
* **Issue Tracking (`/auditor/issues`)**:
  * Severity-classified discrepancies (`critical`, `warning`, `info`).
  * Resolution workflow and resolution notes.
* **Audit Trail (`/auditor/audit-log`)**:
  * Full chronological action log capturing changes made by Auditors, AI Extraction, and Company Users.
* **Firm & Subscription Management (`/auditor/firm`, `/auditor/subscription`, `/auditor/security`)**:
  * CA Sri Lanka / Auditing firm credentials and branding.
  * Subscription tier status and customer portal redirection.
  * Password updates, 2FA status, and global session revocation.

---

## 📡 API Endpoint Index

### 🏢 Business Endpoints
| HTTP Method | Path | Description |
|---|---|---|
| `GET` | `/business/dashboard` | High-level business overview metrics |
| `GET` | `/business/me` | Current business profile & TIN |
| `PUT` | `/business/me` | Update business metadata |
| `GET` | `/business/financial-years` | List financial years |
| `GET` | `/business/search` | Global search across documents & issues |
| `GET` | `/business/action-required` | List open action items |
| `POST` | `/business/action-required/{id}/resolve` | Resolve an action item |
| `GET` | `/documents` | List company documents |
| `GET` | `/documents/summary` | Uploaded/missing document counts |
| `POST` | `/documents` | Upload a new financial document |
| `GET` | `/documents/{id}` | Document details |
| `GET` | `/documents/{id}/extracted-values` | View extracted OCR values |
| `GET` | `/documents/{id}/download` | Download uploaded file |
| `POST` | `/documents/{id}/replace` | Replace document file |
| `POST` | `/documents/{id}/retry` | Re-run automated extraction |
| `DELETE` | `/documents/{id}` | Delete document |
| `GET` | `/financials/summary` | High-level profit & CIT summary |
| `GET` | `/financials/income-statement` | Structured Income Statement |
| `GET` | `/financials/balance-sheet` | Structured Balance Sheet |
| `GET` | `/financials/trial-balance` | Trial Balance accounts |
| `GET` | `/financials/general-ledger` | General Ledger extract |
| `GET` | `/financials/fixed-assets` | Fixed Asset schedule & tax rates |
| `PATCH` | `/financials/values/{id}` | Update extracted financial figure |
| `GET` | `/auditor-submissions` | List submission packages |
| `POST` | `/auditor-submissions` | Create draft submission package |
| `GET` | `/auditor-submissions/{id}/validation` | Validate required docs & issues |
| `POST` | `/auditor-submissions/{id}/submit` | Submit package to auditor |
| `GET` | `/auditor-submissions/{id}/download` | Download PDF summary package |
| `GET` | `/auditor-invitations` | List sent auditor invitations |
| `POST` | `/auditor-invitations` | Invite an auditor |
| `POST` | `/auditor-invitations/{id}/resend` | Resend invitation |
| `DELETE` | `/auditor-invitations/{id}` | Cancel invitation |
| `GET` | `/auditor-reviews` | List auditor reviews |
| `GET` | `/auditor-reviews/{id}` | Review details and issues |
| `POST` | `/auditor-reviews/{id}/issues/{issue_id}/respond` | Submit response to auditor issue |
| `POST` | `/auditor-reviews/{id}/issues/{issue_id}/attachments` | Upload supporting file for issue |
| `POST` | `/auditor-reviews/{id}/resubmit` | Resubmit review to auditor |
| `GET` | `/business/reports` | List available tax reports |
| `GET` | `/business/reports/summary` | Tax & financial summary report |
| `GET` | `/business/reports/summary/pdf` | Download tax summary PDF |
| `GET` | `/notifications` | List notifications |
| `PATCH` | `/notifications/{id}/read` | Mark notification read |
| `GET` | `/settings/company` | Company settings |
| `PUT` | `/settings/company` | Update company settings |
| `GET` | `/settings/financial-years` | Financial years list |
| `POST` | `/settings/financial-years` | Create financial year |
| `GET` | `/settings/users` | List company team members |
| `POST` | `/settings/users/invite` | Invite team member |
| `GET` | `/settings/security` | Security & session configuration |
| `GET` | `/settings/audit-log` | Immutable company audit log |

---

### 🔍 Auditor Endpoints
| HTTP Method | Path | Description |
|---|---|---|
| `GET` | `/auditor/dashboard/summary` | Total companies, pending reviews, critical issues |
| `GET` | `/auditor/dashboard/workload` | Reviews categorized by stage |
| `GET` | `/auditor/dashboard/priority-reviews` | High-risk & urgent review items |
| `GET` | `/auditor/dashboard/recent-activity` | Global activity feed |
| `GET` | `/auditor/dashboard/upcoming-deadlines` | Approaching statutory filing dates |
| `GET` | `/auditor/companies` | Filterable list of assigned companies |
| `POST` | `/auditor/companies` | Add new client company |
| `POST` | `/auditor/companies/import` | Bulk import client companies |
| `GET` | `/auditor/companies/{id}` | Company audit detail |
| `PATCH` | `/auditor/companies/{id}` | Update CIT/Review status & progress |
| `DELETE` | `/auditor/companies/{id}` | Delete company |
| `GET` | `/auditor/review-queue` | Queue filtered by review tabs & risk |
| `POST` | `/auditor/review-queue/{id}/approve` | Approve company tax filing |
| `POST` | `/auditor/review-queue/{id}/request-information` | Request clarification from business |
| `GET` | `/auditor/issues` | List discrepancies across companies |
| `GET` | `/auditor/issues/summary` | Discrepancy counts (critical, warning, info) |
| `POST` | `/auditor/issues/{id}/resolve` | Mark issue resolved with note |
| `GET` | `/auditor/audit-log` | Filterable auditor audit trail |
| `GET` | `/auditor/me` | Auditor profile |
| `PUT` | `/auditor/me` | Update auditor profile |
| `POST` | `/auditor/me/photo` | Upload profile avatar |
| `GET` | `/auditor/firm` | Firm details & registration number |
| `PUT` | `/auditor/firm` | Update firm details |
| `GET` | `/auditor/notifications` | Notification preferences |
| `PUT` | `/auditor/notifications` | Update notification preferences |
| `GET` | `/auditor/subscription` | Firm subscription plan & billing info |
| `POST` | `/auditor/subscription/manage` | Hosted billing portal redirection |
| `POST` | `/auditor/security/change-password` | Update account password |
| `GET` | `/auditor/security/two-factor` | Check 2FA factor status |
| `POST` | `/auditor/security/two-factor/disable` | Disable 2FA factor |
| `POST` | `/auditor/security/sessions/revoke-all` | Global device sign out |

---

## ⚙️ Environment Variables & Configuration

Configure `.env` using `.env.example`:

```env
# Supabase & PostgreSQL Connection
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_ANON_KEY=your-supabase-anon-key

# Direct / Pooled PostgreSQL connection
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# JWT & Security settings
SECRET_KEY=taxeaselk-secret-key-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 🏃 Starting the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

Interactive OpenAPI Swagger UI is available at `/docs` and ReDoc at `/redoc`.
