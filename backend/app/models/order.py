from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=True)
    order_amount = Column(Float, nullable=False)
    commission_amount = Column(Float, default=0.0)
    status = Column(String(20), default="pending")  # pending, processing, completed, cancelled
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    retailer = relationship("Retailer", back_populates="orders")
