"""
TaxEaseLK — Combined Backend API
Corporate Tax Document & Auditor Collaboration Platform for Sri Lankan Pvt Ltd companies.
Integrates with Supabase & PostgreSQL.
"""

import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables

# ── Business routers ──────────────────────────────────────────
from API.routers import business_dashboard      as business_dashboard_module
from API.routers import business                as business_module
from API.routers import action_required         as action_required_module
from API.routers import reports                 as reports_module
from API.routers import business_notifications  as business_notifications_module
from API.routers import documents               as documents_module
from API.routers import financials              as financials_module
from API.routers import auditor_submissions     as auditor_submissions_module
from API.routers import auditor_invitations     as auditor_invitations_module
from API.routers import auditor_reviews         as auditor_reviews_module
from API.routers import settings                as settings_module

# ── Auditor routers ───────────────────────────────────────────
from API.routers import auditor_dashboard       as auditor_dashboard_module
from API.routers import auditors                as auditors_module
from API.routers import companies               as companies_module
from API.routers import review_queue            as review_queue_module
from API.routers import issues                  as issues_module
from API.routers import audit_log               as audit_log_module
from API.routers import firm                    as firm_module
from API.routers import auditor_notifications   as auditor_notifications_module
from API.routers import subscription            as subscription_module
from API.routers import security                as security_module


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    try:
        create_tables()
    except Exception as e:
        print(f"Database initialization warning: {e}")
    yield


# ── App setup ─────────────────────────────────────────────────
app = FastAPI(
    title="TaxEaseLK API",
    description="AI-powered Corporate Tax Document & Auditor Collaboration Platform for Sri Lankan Pvt Ltd companies.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Business routes ───────────────────────────────────────────
app.include_router(business_dashboard_module.router)
app.include_router(business_module.router)
app.include_router(action_required_module.router)
app.include_router(reports_module.router)
app.include_router(business_notifications_module.router)
app.include_router(documents_module.router)
app.include_router(financials_module.router)
app.include_router(auditor_submissions_module.router)
app.include_router(auditor_invitations_module.router)
app.include_router(auditor_reviews_module.router)
app.include_router(settings_module.router)

# ── Auditor routes ────────────────────────────────────────────
app.include_router(auditor_dashboard_module.router)
app.include_router(auditors_module.router)
app.include_router(companies_module.router)
app.include_router(review_queue_module.router)
app.include_router(issues_module.router)
app.include_router(audit_log_module.router)
app.include_router(firm_module.router)
app.include_router(auditor_notifications_module.router)
app.include_router(subscription_module.router)
app.include_router(security_module.router)


# ── Health check & root endpoints ─────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": "TaxEaseLK Backend API",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
