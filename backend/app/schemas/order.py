from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class OrderCreate(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr] = None
    customer_phone: str
    referral_code: str
    order_amount: float

    @field_validator("order_amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Order amount must be greater than 0")
        return round(v, 2)


class OrderOut(BaseModel):
    order_number: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    order_amount: float
    commission_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
