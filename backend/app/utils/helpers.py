from app.config import settings


def generate_retailer_code(owner_name: str, sequence: int) -> str:
    """
    Generate a unique retailer / referral code.
    Takes first 2 letters of the owner's name + zero-padded sequence.
    Example: "Priya Sharma", 1  →  "PS001"
    """
    parts = owner_name.strip().upper().split()
    if len(parts) >= 2:
        prefix = parts[0][0] + parts[1][0]
    elif len(parts) == 1 and len(parts[0]) >= 2:
        prefix = parts[0][:2]
    else:
        prefix = (parts[0][0] + "X") if parts else "XX"
    return f"{prefix}{str(sequence).zfill(3)}"


def generate_referral_link(referral_code: str) -> str:
    return f"{settings.BASE_URL}/?ref={referral_code}"


def generate_order_number(order_id: int) -> str:
    return f"ORD{str(order_id).zfill(4)}"
