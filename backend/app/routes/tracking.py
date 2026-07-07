from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.models.retailer import Retailer
from app.models.scan import Scan
from app.models.whatsapp_click import WhatsAppClick
from app.models.payout import Payout
from app.schemas.scan import ScanCreate, WhatsAppClickCreate
from app.schemas.payout import PayoutRequest
from app.auth.dependencies import get_current_retailer

router = APIRouter()


def _resolve_retailer(code: str, db: Session) -> Retailer:
    retailer = (
        db.query(Retailer)
        .filter(Retailer.referral_code == code.upper(), Retailer.is_active == True)
        .first()
    )
    if not retailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code.",
        )
    return retailer


def _get_client_ip(request: Request) -> str:
    """Extract real IP, respecting X-Forwarded-For header."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─────────────────────────────────────────────
#  QR / Link Scan Tracking
# ─────────────────────────────────────────────

@router.post("/track-scan")
def track_scan(data: ScanCreate, request: Request, db: Session = Depends(get_db)):
    """
    Called by the frontend whenever someone visits the site via a referral link or QR scan.
    Source must be: qr | whatsapp | website
    """
    retailer = _resolve_retailer(data.referral_code, db)

    scan = Scan(
        retailer_id=retailer.id,
        visitor_id=data.visitor_id,
        ip_address=_get_client_ip(request),
        user_agent=(request.headers.get("user-agent", "")[:500] or None),
        source=data.source,
    )
    db.add(scan)
    db.commit()

    return {
        "message": "Scan recorded.",
        "source": data.source,
        "retailer_code": retailer.retailer_code,
    }


# ─────────────────────────────────────────────
#  WhatsApp Click Tracking
# ─────────────────────────────────────────────

@router.post("/track-whatsapp-click")
def track_whatsapp_click(
    data: WhatsAppClickCreate, request: Request, db: Session = Depends(get_db)
):
    """Called when a retailer's WhatsApp share link is clicked."""
    retailer = _resolve_retailer(data.referral_code, db)

    click = WhatsAppClick(
        retailer_id=retailer.id,
        ip_address=_get_client_ip(request),
    )
    db.add(click)
    db.commit()

    return {"message": "WhatsApp click recorded.", "retailer_code": retailer.retailer_code}


# ─────────────────────────────────────────────
#  Payout Requests
# ─────────────────────────────────────────────

@router.post("/payout-request", status_code=status.HTTP_201_CREATED)
def request_payout(
    data: PayoutRequest,
    current_retailer: Retailer = Depends(get_current_retailer),
    db: Session = Depends(get_db),
):
    if data.amount > (current_retailer.total_commission or 0.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested amount ₹{data.amount} exceeds available commission ₹{current_retailer.total_commission}.",
        )

    pending = (
        db.query(Payout)
        .filter(
            Payout.retailer_id == current_retailer.id,
            Payout.status == "pending",
        )
        .first()
    )
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending payout request. Please wait for it to be processed.",
        )

    payout = Payout(
        retailer_id=current_retailer.id,
        amount=data.amount,
        status="pending",
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)

    return {
        "message": "Payout request submitted successfully.",
        "payout_id": payout.id,
        "amount": payout.amount,
        "status": payout.status,
        "requested_at": payout.requested_at,
    }


@router.get("/payouts")
def list_my_payouts(
    current_retailer: Retailer = Depends(get_current_retailer),
    db: Session = Depends(get_db),
):
    payouts = (
        db.query(Payout)
        .filter(Payout.retailer_id == current_retailer.id)
        .order_by(Payout.requested_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "amount": p.amount,
            "status": p.status,
            "requested_at": p.requested_at,
            "paid_at": p.paid_at,
        }
        for p in payouts
    ]
