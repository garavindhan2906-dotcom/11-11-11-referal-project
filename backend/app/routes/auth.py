from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database.connection import get_db
from app.models.retailer import Retailer
from app.schemas.retailer import RetailerRegister, RetailerLogin
from app.auth.jwt_handler import create_access_token
from app.services.qr_service import generate_qr_code
from app.services.whatsapp_service import build_referral_link
from app.utils.helpers import generate_retailer_code, generate_referral_link

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _retailer_to_dict(retailer: Retailer) -> dict:
    return {
        "id": retailer.id,
        "retailer_code": retailer.retailer_code,
        "shop_name": retailer.shop_name,
        "owner_name": retailer.owner_name,
        "email": retailer.email,
        "phone": retailer.phone,
        "referral_code": retailer.referral_code,
        "referral_link": retailer.referral_link,
        "qr_image": retailer.qr_image,
        "commission_percentage": retailer.commission_percentage,
        "total_commission": retailer.total_commission,
        "is_active": retailer.is_active,
        "created_at": retailer.created_at,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RetailerRegister, db: Session = Depends(get_db)):
    # Check duplicate email
    if db.query(Retailer).filter(Retailer.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Generate unique retailer code
    sequence = db.query(Retailer).count() + 1
    retailer_code = generate_retailer_code(data.owner_name, sequence)

    # Ensure uniqueness in case of collision
    while db.query(Retailer).filter(Retailer.retailer_code == retailer_code).first():
        sequence += 1
        retailer_code = generate_retailer_code(data.owner_name, sequence)

    referral_code = retailer_code  # retailer code doubles as referral code
    referral_link = generate_referral_link(referral_code)

    # Create retailer record
    retailer = Retailer(
        retailer_code=retailer_code,
        shop_name=data.shop_name,
        owner_name=data.owner_name,
        email=data.email,
        phone=data.phone,
        password_hash=pwd_context.hash(data.password),
        referral_code=referral_code,
        referral_link=referral_link,
        commission_percentage=10.0,
        total_commission=0.0,
    )
    db.add(retailer)
    db.commit()
    db.refresh(retailer)

    # Generate QR code and persist the path
    qr_path = generate_qr_code(retailer_code, referral_link)
    retailer.qr_image = qr_path
    db.commit()
    db.refresh(retailer)

    token = create_access_token({"sub": str(retailer.id)})

    return {
        "message": "Registration successful. Welcome to 11:11:11!",
        "access_token": token,
        "token_type": "bearer",
        "retailer": _retailer_to_dict(retailer),
    }


@router.post("/login")
def login(data: RetailerLogin, db: Session = Depends(get_db)):
    retailer = db.query(Retailer).filter(Retailer.email == data.email).first()

    if not retailer or not pwd_context.verify(data.password, retailer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not retailer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact admin.",
        )

    token = create_access_token({"sub": str(retailer.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "retailer": _retailer_to_dict(retailer),
    }


@router.post("/logout")
def logout():
    # JWT is stateless — client deletes the token
    return {"message": "Logged out successfully."}
