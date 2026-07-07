import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import engine
from app.models import (  # noqa: F401 — ensures all models are registered
    Retailer, Customer, Order, Scan, WhatsAppClick, Payout,
)
from app.database.connection import Base
from app.routes import auth, retailer, orders, tracking, admin

# ── Create upload dirs ──────────────────────────────────────────
os.makedirs("uploads/qrcodes", exist_ok=True)

# ── Create all DB tables (safe if they already exist) ───────────
Base.metadata.create_all(bind=engine)

# ── App ─────────────────────────────────────────────────────────
app = FastAPI(
    title="11:11:11 Reseller Platform API",
    description=(
        "Backend API for 11:11:11 Manifestation Perfume Reseller Platform by EVOXU PVT LTD. "
        "Handles retailer auth, QR generation, referral tracking, order management, "
        "commission calculation, and admin operations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Tighten to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (QR images served at /uploads/qrcodes/PS001.png) ──
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Routers ─────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",  tags=["Authentication"])
app.include_router(retailer.router,  prefix="/api",       tags=["Retailer"])
app.include_router(orders.router,    prefix="/api",       tags=["Orders"])
app.include_router(tracking.router,  prefix="/api",       tags=["Tracking"])
app.include_router(admin.router,     prefix="/api/admin", tags=["Admin"])


# ── Health check ────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "11:11:11 Reseller Platform API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
