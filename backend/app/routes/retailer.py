from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.retailer import Retailer
from app.models.scan import Scan
from app.models.whatsapp_click import WhatsAppClick
from app.models.order import Order
from app.auth.dependencies import get_current_retailer
from app.services.whatsapp_service import build_whatsapp_url

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(
    current_retailer: Retailer = Depends(get_current_retailer),
    db: Session = Depends(get_db),
):
    rid = current_retailer.id

    total_scans = (
        db.query(func.count(Scan.id)).filter(Scan.retailer_id == rid).scalar() or 0
    )
    whatsapp_clicks = (
        db.query(func.count(WhatsAppClick.id))
        .filter(WhatsAppClick.retailer_id == rid)
        .scalar() or 0
    )
    total_orders = (
        db.query(func.count(Order.id)).filter(Order.retailer_id == rid).scalar() or 0
    )
    total_sales = (
        db.query(func.sum(Order.order_amount))
        .filter(Order.retailer_id == rid, Order.status != "cancelled")
        .scalar() or 0.0
    )
    total_commission = (
        db.query(func.sum(Order.commission_amount))
        .filter(Order.retailer_id == rid, Order.status != "cancelled")
        .scalar() or 0.0
    )

    # QR-specific scans
    qr_scans = (
        db.query(func.count(Scan.id))
        .filter(Scan.retailer_id == rid, Scan.source == "qr")
        .scalar() or 0
    )

    return {
        "retailer_code": current_retailer.retailer_code,
        "shop_name": current_retailer.shop_name,
        "commission_percentage": current_retailer.commission_percentage,
        "total_scans": total_scans,
        "qr_scans": qr_scans,
        "whatsapp_clicks": whatsapp_clicks,
        "total_orders": total_orders,
        "total_sales": float(total_sales),
        "total_commission": float(total_commission),
    }


@router.get("/retailer/qr")
def get_qr(current_retailer: Retailer = Depends(get_current_retailer)):
    return {
        "referral_code": current_retailer.referral_code,
        "referral_link": current_retailer.referral_link,
        "qr_image": current_retailer.qr_image,
    }


@router.get("/retailer/whatsapp-link")
def get_whatsapp_link(current_retailer: Retailer = Depends(get_current_retailer)):
    url = build_whatsapp_url(current_retailer.shop_name, current_retailer.referral_code)
    return {
        "whatsapp_url": url,
        "referral_code": current_retailer.referral_code,
        "referral_link": current_retailer.referral_link,
    }


@router.get("/retailer/profile")
def get_profile(current_retailer: Retailer = Depends(get_current_retailer)):
    return {
        "id": current_retailer.id,
        "retailer_code": current_retailer.retailer_code,
        "shop_name": current_retailer.shop_name,
        "owner_name": current_retailer.owner_name,
        "email": current_retailer.email,
        "phone": current_retailer.phone,
        "referral_code": current_retailer.referral_code,
        "referral_link": current_retailer.referral_link,
        "qr_image": current_retailer.qr_image,
        "commission_percentage": current_retailer.commission_percentage,
        "total_commission": current_retailer.total_commission,
        "is_active": current_retailer.is_active,
        "created_at": current_retailer.created_at,
    }
