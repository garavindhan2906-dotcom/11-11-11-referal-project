from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), index=True, nullable=True)
    phone = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer")
