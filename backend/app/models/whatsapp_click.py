from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class WhatsAppClick(Base):
    __tablename__ = "whatsapp_clicks"

    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    retailer = relationship("Retailer", back_populates="whatsapp_clicks")
