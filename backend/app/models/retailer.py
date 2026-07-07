from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id = Column(Integer, primary_key=True, index=True)
    retailer_code = Column(String(20), unique=True, index=True, nullable=False)
    shop_name = Column(String(200), nullable=False)
    owner_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    referral_code = Column(String(20), unique=True, index=True, nullable=False)
    referral_link = Column(String(500), nullable=False)
    qr_image = Column(String(500), nullable=True)
    commission_percentage = Column(Float, default=10.0)
    total_commission = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    scans = relationship("Scan", back_populates="retailer", cascade="all, delete-orphan")
    whatsapp_clicks = relationship("WhatsAppClick", back_populates="retailer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="retailer")
    payouts = relationship("Payout", back_populates="retailer", cascade="all, delete-orphan")
