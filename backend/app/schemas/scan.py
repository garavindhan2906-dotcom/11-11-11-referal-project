from pydantic import BaseModel, field_validator
from typing import Optional


VALID_SOURCES = {"qr", "whatsapp", "website"}


class ScanCreate(BaseModel):
    referral_code: str
    source: str = "qr"
    visitor_id: Optional[str] = None

    @field_validator("source")
    @classmethod
    def valid_source(cls, v: str) -> str:
        if v not in VALID_SOURCES:
            return "website"
        return v


class WhatsAppClickCreate(BaseModel):
    referral_code: str
