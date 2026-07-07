from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, paid
    requested_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    retailer = relationship("Retailer", back_populates="payouts")
