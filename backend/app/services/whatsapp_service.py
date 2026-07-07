import urllib.parse
from app.config import settings


def build_referral_link(referral_code: str) -> str:
    return f"{settings.BASE_URL}/?ref={referral_code}"


def build_whatsapp_message(shop_name: str, referral_code: str) -> str:
    link = build_referral_link(referral_code)
    return (
        f"✨ *Discover 11:11:11 — Ritual-Infused Manifestation Perfume Oils*\n\n"
        f"Sacred attars crafted for your manifestation journey.\n"
        f"Alcohol-free · 10ml Roll-On · 8-12 Hour Longevity\n\n"
        f"🛍️ Shop Here:\n{link}\n\n"
        f"Shared with love by *{shop_name}* 🌟\n\n"
        f"Use code *NEWUSER20* for 20% off your first order!"
    )


def build_whatsapp_url(shop_name: str, referral_code: str) -> str:
    message = build_whatsapp_message(shop_name, referral_code)
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded}"
