from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.retailer import Retailer
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.order import OrderCreate
from app.auth.dependencies import get_current_retailer
from app.services.commission_service import calculate_commission
from app.utils.helpers import generate_order_number

router = APIRouter()


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """
    Public endpoint — called when a customer places an order via the website.
    The referral_code ties the order to a retailer.
    """
    # 1. Resolve retailer from referral code
    retailer = (
        db.query(Retailer)
        .filter(
            Retailer.referral_code == data.referral_code.upper(),
            Retailer.is_active == True,
        )
        .first()
    )
    if not retailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code.",
        )

    # 2. Find existing customer by phone or create new one
    customer = (
        db.query(Customer).filter(Customer.phone == data.customer_phone).first()
    )
    if not customer:
        customer = Customer(
            name=data.customer_name,
            email=data.customer_email,
            phone=data.customer_phone,
        )
        db.add(customer)
        db.flush()  # get customer.id without full commit

    # 3. Calculate commission
    commission_amount = calculate_commission(
        data.order_amount, retailer.commission_percentage
    )

    # 4. Create order with a temporary order_number
    order = Order(
        order_number="TEMP",
        customer_id=customer.id,
        retailer_id=retailer.id,
        order_amount=data.order_amount,
        commission_amount=commission_amount,
        status="pending",
    )
    db.add(order)
    db.flush()  # get order.id

    # 5. Now set the real order number
    order.order_number = generate_order_number(order.id)

    # 6. Update retailer's cumulative commission
    retailer.total_commission = round(
        (retailer.total_commission or 0.0) + commission_amount, 2
    )

    db.commit()
    db.refresh(order)

    return {
        "message": "Order placed successfully.",
        "order_number": order.order_number,
        "customer_name": customer.name,
        "order_amount": order.order_amount,
        "commission_amount": order.commission_amount,
        "retailer_code": retailer.retailer_code,
        "status": order.status,
    }


@router.get("/orders")
def list_my_orders(
    current_retailer: Retailer = Depends(get_current_retailer),
    db: Session = Depends(get_db),
):
    """Returns all orders attributed to the logged-in retailer."""
    orders = (
        db.query(Order)
        .filter(Order.retailer_id == current_retailer.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    result = []
    for o in orders:
        customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
        result.append(
            {
                "order_number": o.order_number,
                "customer_name": customer.name if customer else "—",
                "customer_phone": customer.phone if customer else "—",
                "order_amount": o.order_amount,
                "commission_amount": o.commission_amount,
                "status": o.status,
                "created_at": o.created_at,
            }
        )
    return result


@router.get("/commissions")
def list_commissions(
    current_retailer: Retailer = Depends(get_current_retailer),
    db: Session = Depends(get_db),
):
    """Returns commission breakdown per order for the logged-in retailer."""
    orders = (
        db.query(Order)
        .filter(
            Order.retailer_id == current_retailer.id,
            Order.status != "cancelled",
        )
        .order_by(Order.created_at.desc())
        .all()
    )

    return [
        {
            "order_number": o.order_number,
            "order_amount": o.order_amount,
            "commission": o.commission_amount,
            "status": o.status,
            "date": o.created_at,
        }
        for o in orders
    ]
