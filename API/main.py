from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
# ─── Routers ─────────────────────────────────────────────────────────────────
from routers.dashboard       import router as dashboard_router
from routers.business        import router as business_router
from routers.action_required import router as action_required_router
from routers.reports         import router as reports_router
from routers.notifications   import router as notifications_router

# ─── App setup ───────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "TaxEase LK API",
    description = "Backend API for TaxEase LK – AI-powered CIT filing for Sri Lankan Pvt Ltd companies.",
    version     = "1.0.0",
    docs_url    = "/docs",       # Swagger UI  →  http://localhost:8000/docs
    redoc_url   = "/redoc",      # ReDoc UI    →  http://localhost:8000/redoc
)

# ─── CORS (allow your React/Vue frontend) ────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://localhost:5173"],  # add your prod URL here
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── Create DB tables on startup ─────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    create_tables()
    print("✅  Database tables created / verified.")

# ─── Register routers ────────────────────────────────────────────────────────

app.include_router(dashboard_router)
app.include_router(business_router)
app.include_router(action_required_router)
app.include_router(reports_router)
app.include_router(notifications_router)

# ─── Health check ────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "TaxEase LK API is running 🚀"}