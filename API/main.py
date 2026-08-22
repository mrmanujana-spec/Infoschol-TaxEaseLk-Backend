import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables

import routers.dashboard       as dashboard_module
import routers.business        as business_module
import routers.action_required as action_required_module
import routers.reports         as reports_module
import routers.notifications   as notifications_module
import routers.documents       as documents_module

app = FastAPI(
    title="TaxEase LK API",
    description="AI-powered CIT filing for Sri Lankan Pvt Ltd companies.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_tables()
    print("Database ready.")

app.include_router(dashboard_module.router)
app.include_router(business_module.router)
app.include_router(action_required_module.router)
app.include_router(reports_module.router)
app.include_router(notifications_module.router)
app.include_router(documents_module.router)

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "TaxEase LK API is running"}