import random
import string
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Product, ProductImage, Reel, ReelComment, Customer, Order, OrderItem, PageView, ProductClick
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
        "gallery": [
            {"id": img.id, "url": request.build_absolute_uri(img.image.url), "position": img.position}
            for img in p.images.all()
        ],
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
        for i in range(8):
            key = f"image_{i}"
            if key in request.FILES:
                ProductImage.objects.create(product=product, image=request.FILES[key], position=i)
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
        # Delete gallery images flagged for removal
        delete_ids = request.data.get("delete_image_ids", "")
        if delete_ids:
            for raw_id in str(delete_ids).split(","):
                try:
                    gimg = ProductImage.objects.get(id=int(raw_id.strip()), product=product)
                    gimg.image.delete(save=False)
                    gimg.delete()
                except (ProductImage.DoesNotExist, ValueError):
                    pass
        # Add new gallery images (image_0 … image_7)
        existing_count = product.images.count()
        for i in range(8):
            key = f"image_{i}"
            if key in request.FILES:
                ProductImage.objects.create(product=product, image=request.FILES[key], position=existing_count + i)
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


class ProductImageDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        try:
            img = ProductImage.objects.get(pk=pk)
            img.image.delete(save=False)
            img.delete()
            return Response({"success": True})
        except ProductImage.DoesNotExist:
            return Response({"error": "Not found."}, status=404)


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
        address = data.get("address", {})

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
            address_name=address.get("name", "").strip(),
            address_phone=address.get("phone", "").strip(),
            address_line1=address.get("line1", "").strip(),
            address_city=address.get("city", "").strip(),
            address_state=address.get("state", "").strip(),
            address_pincode=address.get("pincode", "").strip(),
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


def _reel_data(r, request):
    return {
        "id": r.id,
        "video_url": request.build_absolute_uri(r.video.url) if r.video else None,
        "thumbnail_url": request.build_absolute_uri(r.thumbnail.url) if r.thumbnail else None,
        "caption": r.caption,
        "is_active": r.is_active,
        "likes_count": r.likes_count,
        "comments_count": r.comments.count(),
    }


class ReelsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        reels = Reel.objects.filter(is_active=True)
        return Response([_reel_data(r, request) for r in reels])


class ReelCreateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        if "video" not in request.FILES:
            return Response({"error": "A video file is required."}, status=400)
        reel = Reel(
            video=request.FILES["video"],
            caption=request.data.get("caption", "").strip(),
        )
        if "thumbnail" in request.FILES:
            reel.thumbnail = request.FILES["thumbnail"]
        reel.save()
        return Response({"success": True, **_reel_data(reel, request)}, status=201)


class ReelAdminListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        reels = Reel.objects.all()
        return Response([_reel_data(r, request) for r in reels])


class ReelDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)
        try:
            reel = Reel.objects.get(pk=pk)
        except Reel.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        if reel.video:
            reel.video.delete(save=False)
        if reel.thumbnail:
            reel.thumbnail.delete(save=False)
        reel.delete()
        return Response({"success": True})


class ReelLikeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            reel = Reel.objects.get(pk=pk)
        except Reel.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        reel.likes_count = F("likes_count") + 1
        reel.save(update_fields=["likes_count"])
        reel.refresh_from_db()
        return Response({"success": True, "likes_count": reel.likes_count})


class ReelCommentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        comments = ReelComment.objects.filter(reel_id=pk)
        return Response([
            {
                "id": c.id,
                "name": c.name or "Guest",
                "text": c.text,
                "created_at": c.created_at.strftime("%d %b %Y, %I:%M %p"),
            }
            for c in comments
        ])

    def post(self, request, pk):
        try:
            reel = Reel.objects.get(pk=pk)
        except Reel.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        text = request.data.get("text", "").strip()[:500]
        name = request.data.get("name", "").strip()[:100]
        if not text:
            return Response({"error": "Comment cannot be empty."}, status=400)
        comment = ReelComment.objects.create(reel=reel, name=name, text=text)
        return Response({
            "success": True,
            "id": comment.id,
            "name": comment.name or "Guest",
            "text": comment.text,
            "created_at": comment.created_at.strftime("%d %b %Y, %I:%M %p"),
        }, status=201)


class TrackPageViewView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        path = request.data.get("path", "").strip()[:300]
        visitor_id = request.data.get("visitor_id", "").strip()[:64]
        if not path or not visitor_id:
            return Response({"error": "Missing path or visitor_id."}, status=400)
        pv = PageView.objects.create(path=path, visitor_id=visitor_id)
        return Response({"id": pv.id}, status=201)


class TrackPageDurationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            pv = PageView.objects.get(pk=pk)
        except PageView.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        try:
            pv.duration_seconds = max(0, int(request.data.get("duration", 0)))
            pv.save(update_fields=["duration_seconds"])
        except (TypeError, ValueError):
            pass
        return Response({"success": True})


class TrackProductClickView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        product_id = request.data.get("product_id")
        product_name = request.data.get("product_name", "").strip()[:200]
        visitor_id = request.data.get("visitor_id", "").strip()[:64]
        product = None
        if product_id:
            try:
                product = Product.objects.filter(id=int(product_id)).first()
            except (TypeError, ValueError):
                pass
        ProductClick.objects.create(
            product=product,
            product_name=product_name or (product.name if product else ""),
            visitor_id=visitor_id,
        )
        return Response({"success": True}, status=201)


class AnalyticsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)

        total_views = PageView.objects.count()
        unique_visitors = PageView.objects.values("visitor_id").distinct().count()
        avg_duration = PageView.objects.filter(duration_seconds__isnull=False).aggregate(
            v=Avg("duration_seconds")
        )["v"] or 0

        pages = list(
            PageView.objects.values("path")
            .annotate(views=Count("id"), avg_time=Avg("duration_seconds"))
            .order_by("-views")[:20]
        )
        for p in pages:
            p["avg_time"] = round(p["avg_time"], 1) if p["avg_time"] else 0

        products = list(
            ProductClick.objects.values("product_name")
            .annotate(clicks=Count("id"))
            .order_by("-clicks")[:20]
        )

        return Response({
            "total_views": total_views,
            "unique_visitors": unique_visitors,
            "avg_duration_seconds": round(avg_duration, 1),
            "pages": pages,
            "products": products,
        })


class AdminOrdersListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)

        orders = (
            Order.objects.select_related("customer", "reseller")
            .prefetch_related("items", "items__product")
            .order_by("-created_at")
        )

        data = []
        for o in orders:
            product_names = ", ".join(
                f"{i.product.name} ×{i.quantity}" for i in o.items.all()
            ) or "—"
            data.append({
                "id": o.id,
                "order_number": o.order_number,
                "product": product_names,
                "customer": o.customer.name if o.customer else "—",
                "customer_email": o.customer.email if o.customer else "—",
                "reseller": o.reseller.name if o.reseller else "Direct",
                "date": o.created_at.strftime("%d %b %Y"),
                "amount": float(o.total_amount),
                "commission": float(o.commission_amount),
                "status": o.status,
                "address": {
                    "name": o.address_name,
                    "phone": o.address_phone,
                    "line1": o.address_line1,
                    "city": o.address_city,
                    "state": o.address_state,
                    "pincode": o.address_pincode,
                },
            })

        return Response({
            "total_orders": len(data),
            "orders": data,
        })


class AdminOrderStatusView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        from resellers.views import ADMIN_SECRET
        if request.headers.get("X-Admin-Key") != ADMIN_SECRET:
            return Response({"error": "Unauthorized."}, status=401)

        status_value = request.data.get("status", "").strip()
        valid_statuses = [c[0] for c in Order.STATUS_CHOICES]
        if status_value not in valid_statuses:
            return Response({"error": "Invalid status."}, status=400)

        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        order.status = status_value
        order.save(update_fields=["status"])
        return Response({"success": True, "status": order.status})
