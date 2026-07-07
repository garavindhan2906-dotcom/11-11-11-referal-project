from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    visitor_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    source = Column(String(20), nullable=False, default="qr")  # qr, whatsapp, website
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    retailer = relationship("Retailer", back_populates="scans")
