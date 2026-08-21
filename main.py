"""
Run with:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs to see and test every endpoint.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auditors,
    companies,
    notifications,
    review_queue,
    issues,
    audit_log,
    dashboard,
    firm,
    subscription,
    security,
)

app = FastAPI(
    title="TaxEaseLK — Auditor Workspace API",
    description="Backend API for the TaxEaseLK auditor workspace: manage assigned companies, "
    "review CIT computations, track issues, and view the audit trail.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to your real frontend URL before going live
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(companies.router)
app.include_router(review_queue.router)
app.include_router(issues.router)
app.include_router(audit_log.router)
app.include_router(auditors.router)
app.include_router(firm.router)
app.include_router(notifications.router)
app.include_router(subscription.router)
app.include_router(security.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
