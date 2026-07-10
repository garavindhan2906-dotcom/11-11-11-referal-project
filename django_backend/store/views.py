import random
import string
from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Product, Customer, Order, OrderItem
from resellers.models import Reseller


def _order_number(prefix="ORD"):
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{timezone.now().strftime('%m%d')}-{suffix}"


def _product_data(p, request):
    return {
        "id": p.id,
        "name": p.name,
        "intent": p.intent,
        "description": p.description,
        "price": float(p.price),
        "for_gender": p.for_gender,
        "emoji": p.emoji,
        "in_stock": p.in_stock,
        "image_url": request.build_absolute_uri(p.image.url) if p.image else None,
        "video_url": request.build_absolute_uri(p.video.url) if p.video else None,
    }


class ProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.all()
        return Response([_product_data(p, request) for p in products])


class ProductCreateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "Product name is required."}, status=400)
        in_stock_raw = request.data.get("in_stock", "true")
        in_stock = in_stock_raw if isinstance(in_stock_raw, bool) else str(in_stock_raw).lower() != "false"
        product = Product(
            name=name,
            intent=request.data.get("intent", ""),
            price=request.data.get("price", 1234),
            for_gender=request.data.get("for_gender", "male"),
            emoji=request.data.get("emoji", "✦"),
            description=request.data.get("description", ""),
            in_stock=in_stock,
        )
        if "image" in request.FILES:
            product.image = request.FILES["image"]
        if "video" in request.FILES:
            product.video = request.FILES["video"]
        product.save()
        return Response({"success": True, **_product_data(product, request)}, status=201)


class ProductUpdateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request, pk):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        for field in ["name", "intent", "description", "price", "for_gender", "emoji"]:
            if field in request.data:
                setattr(product, field, request.data[field])
        in_stock_raw = request.data.get("in_stock")
        if in_stock_raw is not None:
            product.in_stock = in_stock_raw if isinstance(in_stock_raw, bool) else str(in_stock_raw).lower() != "false"
        if "image" in request.FILES:
            if product.image:
                product.image.delete(save=False)
            product.image = request.FILES["image"]
        if "video" in request.FILES:
            if product.video:
                product.video.delete(save=False)
            product.video = request.FILES["video"]
        product.save()
        return Response({"success": True, **_product_data(product, request)})


class ProductDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        if product.image:
            product.image.delete(save=False)
        if product.video:
            product.video.delete(save=False)
        product.delete()
        return Response({"success": True})


class PlaceOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        ref_code = data.get("ref_code", "").strip().upper()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        name = data.get("name", "").strip()
        items = data.get("items", [])
        total = data.get("total", 0)

        if not email or not name or not items:
            return Response({"error": "Missing required fields."}, status=400)

        reseller = None
        if ref_code:
            try:
                reseller = Reseller.objects.get(reseller_code=ref_code, is_active=True)
            except Reseller.DoesNotExist:
                pass

        customer, _ = Customer.objects.get_or_create(
            email=email,
            defaults={"name": name, "phone": phone, "referred_by": reseller},
        )
        if not customer.referred_by and reseller:
            customer.referred_by = reseller
            customer.save()
        if phone and not customer.phone:
            customer.phone = phone
            customer.save()

        total_qty = sum(int(i.get("quantity", 1)) for i in items)
        commission_amount = total_qty * float(reseller.commission_rate) if reseller else 0

        prefix = reseller.reseller_code if reseller else "ORD"
        order = Order.objects.create(
            order_number=_order_number(prefix),
            customer=customer,
            reseller=reseller,
            total_amount=total,
            commission_amount=commission_amount,
            status="pending",
        )

        for item in items:
            product = None
            try:
                product = Product.objects.get(id=item["product_id"])
            except (Product.DoesNotExist, KeyError, ValueError, TypeError):
                raw = item.get("product_name", "")
                base_name = raw.split("-")[0].strip() if "-" in raw else raw.strip()
                if base_name:
                    product = Product.objects.filter(name__iexact=base_name).first()
            if product:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.get("quantity", 1),
                    unit_price=product.price,
                )

        return Response({
            "success": True,
            "order_number": order.order_number,
            "reseller": reseller.name if reseller else None,
        })


class ResellerSalesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)

        total_orders = Order.objects.count()
        total_revenue = float(Order.objects.aggregate(v=Sum("total_amount"))["v"] or 0)
        total_commission = float(Order.objects.aggregate(v=Sum("commission_amount"))["v"] or 0)

        resellers_data = []
        for r in Reseller.objects.filter(is_active=True).order_by("name"):
            orders = Order.objects.filter(reseller=r)
            order_count = orders.count()
            revenue = float(orders.aggregate(v=Sum("total_amount"))["v"] or 0)
            commission = float(orders.aggregate(v=Sum("commission_amount"))["v"] or 0)

            products = (
                OrderItem.objects
                .filter(order__reseller=r)
                .values("product__name", "product__emoji")
                .annotate(total_qty=Sum("quantity"), total_rev=Sum("unit_price"))
                .order_by("-total_qty")
            )

            resellers_data.append({
                "id": r.id,
                "name": r.name,
                "code": r.reseller_code,
                "reseller_id": r.reseller_id,
                "reseller_type": r.reseller_type,
                "orders": order_count,
                "revenue": revenue,
                "commission": commission,
                "products": [
                    {
                        "name": p["product__name"],
                        "emoji": p["product__emoji"] or "✦",
                        "qty": p["total_qty"],
                        "revenue": float(p["total_rev"] or 0),
                    }
                    for p in products
                ],
            })

        direct = Order.objects.filter(reseller__isnull=True)
        return Response({
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_commission": total_commission,
            "direct_orders": direct.count(),
            "direct_revenue": float(direct.aggregate(v=Sum("total_amount"))["v"] or 0),
            "resellers": resellers_data,
        })


class CalendarView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        from resellers.models import Reseller, ResellerApplication
        import calendar as cal
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)

        try:
            year  = int(request.GET.get("year",  timezone.now().year))
            month = int(request.GET.get("month", timezone.now().month))
        except ValueError:
            return Response({"error": "Invalid year/month."}, status=400)

        # date range for the month
        first = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
        last_day = cal.monthrange(year, month)[1]
        last  = timezone.datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.get_current_timezone())

        # orders this month
        orders_qs = (
            Order.objects
            .filter(created_at__gte=first, created_at__lte=last)
            .select_related("customer", "reseller")
            .prefetch_related("items__product")
            .order_by("created_at")
        )

        # resellers joined this month
        resellers_qs = Reseller.objects.filter(created_at__gte=first, created_at__lte=last).order_by("created_at")

        # applications this month
        apps_qs = ResellerApplication.objects.filter(applied_at__gte=first, applied_at__lte=last).order_by("applied_at")

        # build day-keyed dict
        days = {}

        for o in orders_qs:
            key = o.created_at.strftime("%Y-%m-%d")
            if key not in days:
                days[key] = {"orders": [], "resellers": [], "applications": [], "revenue": 0, "commission": 0}
            first_item = o.items.first()
            days[key]["orders"].append({
                "order_number": o.order_number,
                "customer":     o.customer.name,
                "customer_phone": o.customer.phone or "—",
                "product":      first_item.product.name if first_item else "—",
                "qty":          first_item.quantity if first_item else 1,
                "amount":       float(o.total_amount),
                "commission":   float(o.commission_amount),
                "reseller":     o.reseller.name if o.reseller else "Direct",
                "status":       o.status,
            })
            days[key]["revenue"]    += float(o.total_amount)
            days[key]["commission"] += float(o.commission_amount)

        for r in resellers_qs:
            key = r.created_at.strftime("%Y-%m-%d")
            if key not in days:
                days[key] = {"orders": [], "resellers": [], "applications": [], "revenue": 0, "commission": 0}
            days[key]["resellers"].append({
                "name": r.name,
                "code": r.reseller_code,
                "phone": r.phone,
                "type": r.reseller_type,
            })

        for a in apps_qs:
            key = a.applied_at.strftime("%Y-%m-%d")
            if key not in days:
                days[key] = {"orders": [], "resellers": [], "applications": [], "revenue": 0, "commission": 0}
            days[key]["applications"].append({
                "name":   a.name,
                "phone":  a.phone,
                "store":  a.store_name or "—",
                "status": a.status,
            })

        # month summary
        total_orders   = sum(len(d["orders"])      for d in days.values())
        total_revenue  = sum(d["revenue"]           for d in days.values())
        total_commission = sum(d["commission"]      for d in days.values())
        total_resellers  = sum(len(d["resellers"])  for d in days.values())

        return Response({
            "year": year, "month": month,
            "days": days,
            "summary": {
                "total_orders":     total_orders,
                "total_revenue":    total_revenue,
                "total_commission": total_commission,
                "new_resellers":    total_resellers,
            },
        })
