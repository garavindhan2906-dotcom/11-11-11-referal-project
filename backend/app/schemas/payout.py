from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class PayoutRequest(BaseModel):
    amount: float

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return round(v, 2)


class PayoutOut(BaseModel):
    id: int
    amount: float
    status: str
    requested_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True
