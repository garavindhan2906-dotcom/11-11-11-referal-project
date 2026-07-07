def calculate_commission(order_amount: float, commission_percentage: float) -> float:
    """
    Calculate commission.
    Example: order_amount=2500, commission_percentage=10 → 250.0
    """
    return round((order_amount * commission_percentage) / 100, 2)
