# Import all models here so SQLAlchemy discovers them for Base.metadata.create_all()
from app.models.retailer import Retailer
from app.models.customer import Customer
from app.models.order import Order
from app.models.scan import Scan
from app.models.whatsapp_click import WhatsAppClick
from app.models.payout import Payout
