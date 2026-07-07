from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class RetailerRegister(BaseModel):
    shop_name: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("shop_name", "owner_name", "phone")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class RetailerLogin(BaseModel):
    email: EmailStr
    password: str


class RetailerOut(BaseModel):
    id: int
    retailer_code: str
    shop_name: str
    owner_name: str
    email: str
    phone: str
    referral_code: str
    referral_link: str
    qr_image: Optional[str]
    commission_percentage: float
    total_commission: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
