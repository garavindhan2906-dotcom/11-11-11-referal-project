from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database.connection import get_db
from app.models.retailer import Retailer
from app.models.order import Order
from app.models.scan import Scan
from app.models.whatsapp_click import WhatsAppClick
from app.models.payout import Payout
from app.models.customer import Customer
from app.config import settings

router = APIRouter()


def verify_admin(x_admin_key: Optional[str] = Header(None)) -> bool:
    """Simple header-based admin auth. Pass X-Admin-Key in request headers."""
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key.",
        )
    return True


# ─────────────────────────────────────────────
#  Admin Dashboard
# ─────────────────────────────────────────────

@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    total_retailers = db.query(func.count(Retailer.id)).scalar() or 0
    active_retailers = (
        db.query(func.count(Retailer.id))
        .filter(Retailer.is_active == True)
        .scalar() or 0
    )
    total_customers = db.query(func.count(Customer.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "pending")
        .scalar() or 0
    )
    total_sales = (
        db.query(func.sum(Order.order_amount))
        .filter(Order.status != "cancelled")
        .scalar() or 0.0
    )
    total_commission = (
        db.query(func.sum(Order.commission_amount))
        .filter(Order.status != "cancelled")
        .scalar() or 0.0
    )
    total_scans = db.query(func.count(Scan.id)).scalar() or 0
    total_whatsapp_clicks = db.query(func.count(WhatsAppClick.id)).scalar() or 0
    pending_payouts = (
        db.query(func.count(Payout.id))
        .filter(Payout.status == "pending")
        .scalar() or 0
    )
    pending_payout_amount = (
        db.query(func.sum(Payout.amount))
        .filter(Payout.status == "pending")
        .scalar() or 0.0
    )

    return {
        "total_retailers": total_retailers,
        "active_retailers": active_retailers,
        "total_customers": total_customers,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "total_sales": float(total_sales),
        "total_commission_owed": float(total_commission),
        "total_scans": total_scans,
        "total_whatsapp_clicks": total_whatsapp_clicks,
        "pending_payouts": pending_payouts,
        "pending_payout_amount": float(pending_payout_amount),
    }


# ─────────────────────────────────────────────
#  Retailers
# ─────────────────────────────────────────────

@router.get("/retailers")
def list_retailers(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    retailers = db.query(Retailer).order_by(Retailer.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "retailer_code": r.retailer_code,
            "shop_name": r.shop_name,
            "owner_name": r.owner_name,
            "email": r.email,
            "phone": r.phone,
            "referral_code": r.referral_code,
            "referral_link": r.referral_link,
            "commission_percentage": r.commission_percentage,
            "total_commission": r.total_commission,
            "is_active": r.is_active,
            "created_at": r.created_at,
        }
        for r in retailers
    ]


@router.put("/retailers/{retailer_id}/toggle")
def toggle_retailer(
    retailer_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    retailer = db.query(Retailer).filter(Retailer.id == retailer_id).first()
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found.")
    retailer.is_active = not retailer.is_active
    db.commit()
    state = "activated" if retailer.is_active else "deactivated"
    return {"message": f"Retailer {retailer.retailer_code} has been {state}."}


@router.put("/retailers/{retailer_id}/commission")
def update_commission(
    retailer_id: int,
    commission_percentage: float,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    if not (0 < commission_percentage <= 100):
        raise HTTPException(status_code=400, detail="Commission must be between 0 and 100.")
    retailer = db.query(Retailer).filter(Retailer.id == retailer_id).first()
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found.")
    retailer.commission_percentage = commission_percentage
    db.commit()
    return {"message": f"Commission updated to {commission_percentage}% for {retailer.retailer_code}."}


# ─────────────────────────────────────────────
#  Orders
# ─────────────────────────────────────────────

@router.get("/orders")
def list_orders(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        retailer = db.query(Retailer).filter(Retailer.id == o.retailer_id).first()
        customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
        result.append(
            {
                "order_number": o.order_number,
                "retailer_code": retailer.retailer_code if retailer else None,
                "shop_name": retailer.shop_name if retailer else None,
                "customer_name": customer.name if customer else None,
                "customer_phone": customer.phone if customer else None,
                "order_amount": o.order_amount,
                "commission_amount": o.commission_amount,
                "status": o.status,
                "created_at": o.created_at,
            }
        )
    return result


@router.put("/orders/{order_number}/status")
def update_order_status(
    order_number: str,
    new_status: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    valid = {"pending", "processing", "completed", "cancelled"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    order.status = new_status
    db.commit()
    return {"message": f"Order {order_number} status updated to '{new_status}'."}


# ─────────────────────────────────────────────
#  Payouts
# ─────────────────────────────────────────────

@router.get("/payouts")
def list_payouts(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    payouts = db.query(Payout).order_by(Payout.requested_at.desc()).all()
    result = []
    for p in payouts:
        retailer = db.query(Retailer).filter(Retailer.id == p.retailer_id).first()
        result.append(
            {
                "id": p.id,
                "retailer_code": retailer.retailer_code if retailer else None,
                "shop_name": retailer.shop_name if retailer else None,
                "amount": p.amount,
                "status": p.status,
                "requested_at": p.requested_at,
                "paid_at": p.paid_at,
            }
        )
    return result


@router.put("/payouts/{payout_id}/approve")
def approve_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found.")
    if payout.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending payouts can be approved.")
    payout.status = "approved"
    db.commit()
    return {"message": f"Payout #{payout_id} approved."}


@router.put("/payouts/{payout_id}/mark-paid")
def mark_payout_paid(
    payout_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found.")
    if payout.status not in {"pending", "approved"}:
        raise HTTPException(status_code=400, detail="Payout already paid or invalid state.")
    payout.status = "paid"
    payout.paid_at = datetime.utcnow()
    db.commit()
    return {"message": f"Payout #{payout_id} marked as paid."}
