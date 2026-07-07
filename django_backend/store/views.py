import random
import string
from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Product, Customer, Order, OrderItem
from resellers.models import Reseller


def _order_number(prefix='ORD'):
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{timezone.now().strftime('%m%d')}-{suffix}"


class PlaceOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        ref_code = data.get('ref_code', '').strip().upper()
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        items = data.get('items', [])
        total = data.get('total', 0)

        if not email or not name or not items:
            return Response({'error': 'Missing required fields.'}, status=400)

        reseller = None
        if ref_code:
            try:
                reseller = Reseller.objects.get(reseller_code=ref_code, is_active=True)
            except Reseller.DoesNotExist:
                pass

        customer, _ = Customer.objects.get_or_create(
            email=email,
            defaults={'name': name, 'referred_by': reseller},
        )
        if not customer.referred_by and reseller:
            customer.referred_by = reseller
            customer.save()

        prefix = reseller.reseller_code if reseller else 'ORD'
        order = Order.objects.create(
            order_number=_order_number(prefix),
            customer=customer,
            reseller=reseller,
            total_amount=total,
            commission_amount=float(reseller.commission_rate) if reseller else 0,
            status='pending',
        )

        for item in items:
            product = None
            try:
                product = Product.objects.get(id=item['product_id'])
            except (Product.DoesNotExist, KeyError, ValueError, TypeError):
                # Cart name may have reseller suffix like KLEOMA-BHU — strip it
                raw = item.get('product_name', '')
                base_name = raw.split('-')[0].strip() if '-' in raw else raw.strip()
                if base_name:
                    product = Product.objects.filter(name__iexact=base_name).first()
            if product:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.get('quantity', 1),
                    unit_price=product.price,
                )

        return Response({
            'success': True,
            'order_number': order.order_number,
            'reseller': reseller.name if reseller else None,
        })


class ProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.all()
        return Response([
            {
                'id': p.id,
                'name': p.name,
                'intent': p.intent,
                'price': float(p.price),
                'for_gender': p.for_gender,
                'emoji': p.emoji,
                'in_stock': p.in_stock,
            }
            for p in products
        ])


class ResellerSalesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get('X-Admin-Key') != ADMIN_SECRET:
            return Response({'error': 'Unauthorized.'}, status=401)

        total_orders = Order.objects.count()
        total_revenue = float(Order.objects.aggregate(v=Sum('total_amount'))['v'] or 0)
        total_commission = float(Order.objects.aggregate(v=Sum('commission_amount'))['v'] or 0)

        resellers_data = []
        for r in Reseller.objects.filter(is_active=True).order_by('name'):
            orders = Order.objects.filter(reseller=r)
            order_count = orders.count()
            revenue = float(orders.aggregate(v=Sum('total_amount'))['v'] or 0)
            commission = float(orders.aggregate(v=Sum('commission_amount'))['v'] or 0)

            products = (
                OrderItem.objects
                .filter(order__reseller=r)
                .values('product__name', 'product__emoji')
                .annotate(total_qty=Sum('quantity'), total_rev=Sum('unit_price'))
                .order_by('-total_qty')
            )

            resellers_data.append({
                'id': r.id,
                'name': r.name,
                'code': r.reseller_code,
                'reseller_id': r.reseller_id,
                'reseller_type': r.reseller_type,
                'orders': order_count,
                'revenue': revenue,
                'commission': commission,
                'products': [
                    {
                        'name': p['product__name'],
                        'emoji': p['product__emoji'] or '✦',
                        'qty': p['total_qty'],
                        'revenue': float(p['total_rev'] or 0),
                    }
                    for p in products
                ],
            })

        direct = Order.objects.filter(reseller__isnull=True)
        return Response({
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_commission': total_commission,
            'direct_orders': direct.count(),
            'direct_revenue': float(direct.aggregate(v=Sum('total_amount'))['v'] or 0),
            'resellers': resellers_data,
        })
