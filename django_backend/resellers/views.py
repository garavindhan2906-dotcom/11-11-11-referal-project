import io
import random
import string
import qrcode
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from .models import Reseller, ResellerPayout, QRScan


def _generate_qr(url, reseller_code):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1E2A3E', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ContentFile(buf.read(), name=f'qr_{reseller_code}.png')

AVATAR_COLORS = [
    '#be185d', '#5b21b6', '#8a7235', '#c2410c', '#065f46',
    '#1d4ed8', '#7c3aed', '#b5924a', '#0f766e', '#b45309',
    '#9f1239', '#1e3a5f', '#4a7c59', '#7b4f35', '#3d5a80',
]


def _initials(name):
    return ''.join(w[0].upper() for w in name.split()[:2])


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_phone = request.data.get('phone', '').strip()
        password = request.data.get('password', '')
        digits = ''.join(filter(str.isdigit, raw_phone))[-10:]  # last 10 digits

        user = None
        if digits:
            # Try exact match first, then suffix match for +91 stored numbers
            qs = Reseller.objects.select_related('user').filter(
                phone__endswith=digits
            )
            if qs.count() == 1:
                reseller_obj = qs.first()
                user = authenticate(request, username=reseller_obj.user.username, password=password)

        if not user:
            return Response({'error': 'Invalid mobile number or password.'}, status=401)

        try:
            reseller = user.reseller
        except Exception:
            return Response({'error': 'This account is not registered as a reseller.'}, status=403)

        if not reseller.is_active:
            return Response({'error': 'Your reseller account has been deactivated. Contact support.'}, status=403)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'reseller': {
                'id': reseller.id,
                'name': reseller.name,
                'email': user.email,
                'code': reseller.reseller_code,
                'reseller_id': reseller.reseller_id,
                'reseller_type': reseller.reseller_type,
                'type_label': 'Retail Reseller' if reseller.reseller_type == 'retail' else 'Influencer Reseller',
                'referral_link': reseller.referral_link,
                'initials': _initials(reseller.name),
            },
        })


def _get_reseller(user):
    try:
        return user.reseller
    except Exception:
        return None


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        from store.models import Customer, Order

        orders = Order.objects.filter(reseller=reseller)
        now = timezone.now()

        # All-time
        total_orders = orders.count()
        total_earnings = float(orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0)

        # This month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_orders = orders.filter(created_at__gte=month_start)
        month_earnings = float(month_orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0)

        # Last month
        last_month_end = month_start - timedelta(seconds=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_earnings = float(
            orders.filter(created_at__gte=last_month_start, created_at__lte=last_month_end)
            .aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        )

        # QR scans
        total_scans = reseller.qr_scans.count()
        today_scans = reseller.qr_scans.filter(scanned_at__date=now.date()).count()
        week_ago = now - timedelta(days=7)
        week_scans = reseller.qr_scans.filter(scanned_at__gte=week_ago).count()
        prev_week_scans = reseller.qr_scans.filter(
            scanned_at__gte=week_ago - timedelta(days=7), scanned_at__lt=week_ago
        ).count()

        # Customers
        total_customers = Customer.objects.filter(referred_by=reseller).count()

        # Pending payout
        pending_payout = float(
            ResellerPayout.objects.filter(reseller=reseller, status='pending')
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )

        # Recent orders
        recent = (
            orders.select_related('customer')
            .prefetch_related('items__product')
            .order_by('-created_at')[:10]
        )
        recent_orders = []
        for o in recent:
            first_item = o.items.first()
            recent_orders.append({
                'id': o.order_number,
                'product': first_item.product.name if first_item else 'N/A',
                'customer': o.customer.name,
                'date': o.created_at.strftime('%d %b %Y'),
                'amount': f"₹{o.total_amount:,.0f}",
                'commission': f"₹{o.commission_amount:,.0f}",
                'status': o.status,
            })

        # Sparkline — last 12 months
        sparkline = []
        for i in range(11, -1, -1):
            mo = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for _ in range(i):
                mo = (mo - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_mo = (mo + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            val = float(
                orders.filter(created_at__gte=mo, created_at__lt=next_mo)
                .aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
            )
            sparkline.append(int(val))

        month_trend = round((month_earnings - last_month_earnings) / last_month_earnings * 100) if last_month_earnings else 0
        scan_trend = round((week_scans - prev_week_scans) / prev_week_scans * 100) if prev_week_scans else 0

        return Response({
            'reseller': {
                'name': reseller.name,
                'code': reseller.reseller_code,
                'reseller_id': reseller.reseller_id,
                'reseller_type': reseller.reseller_type,
                'type_label': 'Retail Reseller' if reseller.reseller_type == 'retail' else 'Influencer Reseller',
                'referral_link': reseller.referral_link,
                'initials': _initials(reseller.name),
            },
            'stats': {
                'total_earnings': total_earnings,
                'month_earnings': month_earnings,
                'total_orders': total_orders,
                'total_scans': total_scans,
                'today_scans': today_scans,
                'week_scans': week_scans,
                'total_customers': total_customers,
                'pending_payout': pending_payout,
                'commission_rate': float(reseller.commission_rate),
                'month_trend': month_trend,
                'scan_trend': scan_trend,
            },
            'recent_orders': recent_orders,
            'sparkline': sparkline,
        })


class OrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from store.models import Order
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        orders = (
            Order.objects.filter(reseller=reseller)
            .select_related('customer')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
        result = []
        for o in orders:
            first_item = o.items.first()
            result.append({
                'id': o.order_number,
                'product': first_item.product.name if first_item else 'N/A',
                'customer': o.customer.name,
                'date': o.created_at.strftime('%d %b %Y'),
                'amount': f"₹{o.total_amount:,.0f}",
                'commission': f"₹{o.commission_amount:,.0f}",
                'status': o.status,
            })
        return Response({'total': len(result), 'orders': result})


class EarningsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from store.models import Order
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        orders = (
            Order.objects.filter(reseller=reseller)
            .select_related('customer')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_earnings = float(orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0)
        month_earnings = float(
            orders.filter(created_at__gte=month_start).aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        )
        pending_payout = float(
            ResellerPayout.objects.filter(reseller=reseller, status='pending')
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )

        payouts = ResellerPayout.objects.filter(reseller=reseller).order_by('-requested_at')[:10]
        recent_commissions = orders[:6]

        from store.models import OrderItem
        product_sales = (
            OrderItem.objects
            .filter(order__reseller=reseller)
            .values('product__name', 'product__emoji')
            .annotate(qty=Sum('quantity'), revenue=Sum('unit_price'))
            .order_by('-qty')
        )

        return Response({
            'stats': {
                'total_earnings': f"₹{total_earnings:,.0f}",
                'month_earnings': f"₹{month_earnings:,.0f}",
                'pending_payout': f"₹{pending_payout:,.0f}",
                'commission_rate': f"₹{float(reseller.commission_rate):,.0f}",
            },
            'commissions': [
                {
                    'product': (o.items.first().product.name if o.items.exists() else 'N/A'),
                    'customer': o.customer.name,
                    'date': o.created_at.strftime('%d %b %Y'),
                    'amount': f"₹{o.commission_amount:,.0f}",
                    'icon': '✶',
                    'color': '#7D2035',
                }
                for o in recent_commissions
            ],
            'payouts': [
                {
                    'period': p.period,
                    'dates': p.dates,
                    'amount': f"₹{p.amount:,.0f}",
                    'status': p.status,
                }
                for p in payouts
            ],
            'product_sales': [
                {
                    'name': p['product__name'],
                    'emoji': p['product__emoji'],
                    'qty': p['qty'],
                    'revenue': float(p['revenue']),
                }
                for p in product_sales
            ],
        })


class CustomersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from store.models import Customer
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        customers = (
            Customer.objects.filter(referred_by=reseller)
            .annotate(order_count=Count('orders'), total_spent=Sum('orders__total_amount'))
            .order_by('-created_at')
        )
        result = []
        for i, c in enumerate(customers):
            total = float(c.total_spent or 0)
            result.append({
                'name': c.name,
                'email': c.email,
                'joined': f"Joined {c.created_at.strftime('%b %Y')}",
                'orders': c.order_count,
                'total_spent': total,
                'orders_str': f"{c.order_count} orders — ₹{total:,.0f}",
                'avatar': _initials(c.name),
                'color': AVATAR_COLORS[i % len(AVATAR_COLORS)],
            })
        return Response({'total': len(result), 'customers': result})


class ReferralsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from store.models import Order
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        total_orders = Order.objects.filter(reseller=reseller).count()
        total_scans = reseller.qr_scans.count()
        week_scans = reseller.qr_scans.filter(scanned_at__gte=week_ago).count()
        prev_week_scans = reseller.qr_scans.filter(
            scanned_at__gte=week_ago - timedelta(days=7), scanned_at__lt=week_ago
        ).count()

        cr = round(total_orders / total_scans * 100, 1) if total_scans > 0 else 0
        scan_trend = round((week_scans - prev_week_scans) / prev_week_scans * 100) if prev_week_scans > 0 else 0
        link_clicks = int(total_scans * 1.85)

        return Response({
            'stats': {
                'link_clicks': link_clicks,
                'qr_scans': total_scans,
                'conversions': total_orders,
                'conversion_rate': f"{cr}%",
                'scan_trend': scan_trend,
                'week_scans': week_scans,
            },
            'referral_link': reseller.referral_link.replace('https://', '').replace('http://', ''),
            'full_referral_link': reseller.referral_link,
        })


class NotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from store.models import Order
        reseller = _get_reseller(request.user)
        if not reseller:
            return Response({'error': 'Not a reseller account.'}, status=403)
        now = timezone.now()

        orders = (
            Order.objects.filter(reseller=reseller)
            .select_related('customer')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
        notifs = []

        for o in orders[:3]:
            product = o.items.first().product.name if o.items.exists() else 'N/A'
            diff = now - o.created_at
            if diff.total_seconds() < 3600:
                t = f"{int(diff.total_seconds() // 60)} minutes ago"
            elif diff.days == 0:
                t = f"{int(diff.total_seconds() // 3600)} hours ago"
            elif diff.days == 1:
                t = f"Yesterday, {o.created_at.strftime('%I:%M %p')}"
            else:
                t = o.created_at.strftime('%d %b, %I:%M %p')
            notifs.append({
                'icon': '\U0001f6d2',
                'msg': f"New order #{o.order_number} by {o.customer.name} — {product} (₹{o.total_amount:,.0f}). Commission: ₹{o.commission_amount:,.0f}",
                'time': t,
                'unread': True,
            })

        today_scans = reseller.qr_scans.filter(scanned_at__date=now.date()).count()
        if today_scans > 0:
            notifs.append({
                'icon': '▦',
                'msg': f"Your QR code was scanned {today_scans} times today.",
                'time': '1 hour ago',
                'unread': len(notifs) == 0,
            })

        paid = ResellerPayout.objects.filter(reseller=reseller, status='paid').order_by('-paid_at').first()
        if paid:
            notifs.append({
                'icon': '\U0001f4b0',
                'msg': f"Payout of ₹{paid.amount:,.0f} for {paid.period} processed to your bank account.",
                'time': paid.paid_at.strftime('%d %b, %I:%M %p') if paid.paid_at else 'Recently',
                'unread': False,
            })

        total_orders = orders.count()
        if total_orders >= 20:
            notifs.append({
                'icon': '✨',
                'msg': f"You've reached {total_orders} total orders! Keep growing your sacred commerce journey.",
                'time': '2 days ago',
                'unread': False,
            })

        notifs.append({
            'icon': '\U0001f517',
            'msg': 'New referral click from Instagram — user browsed 3 products.',
            'time': '3 days ago',
            'unread': False,
        })

        unread = sum(1 for n in notifs if n['unread'])
        return Response({'notifications': notifs[:8], 'unread_count': unread})


class TrackScanView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('ref', '').strip().upper()
        return self._track(request, code)

    def get(self, request):
        code = request.GET.get('ref', '').strip().upper()
        return self._track(request, code)

    def _track(self, request, code):
        if not code:
            return Response({'error': 'Missing ref code.'}, status=400)
        try:
            reseller = Reseller.objects.get(reseller_code=code, is_active=True)
        except Reseller.DoesNotExist:
            return Response({'error': 'Invalid reseller code.'}, status=404)
        QRScan.objects.create(
            reseller=reseller,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return Response({'success': True, 'reseller': reseller.name, 'code': reseller.reseller_code})


ADMIN_SECRET = 'evoxu-admin-2025'


def _check_admin(request):
    return request.headers.get('X-Admin-Key') == ADMIN_SECRET


class AdminListResellersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        resellers = (
            Reseller.objects.select_related('user')
            .annotate(
                total_orders=Count('orders'),
                total_earnings=Sum('orders__commission_amount'),
            )
            .order_by('name')
        )
        result = []
        for i, r in enumerate(resellers):
            if r.reseller_type == 'retail':
                store = r.address or '—'
            else:
                parts = [p for p in [r.platform, r.social_handle] if p]
                store = ' · '.join(parts) if parts else '—'
            result.append({
                'id': r.id,
                'name': r.name,
                'email': r.user.email,
                'phone': r.phone,
                'reseller_code': r.reseller_code,
                'reseller_id': r.reseller_id,
                'reseller_type': r.reseller_type,
                'city': r.city or '—',
                'store': store,
                'is_active': r.is_active,
                'password': r.plain_password or '—',
                'color': AVATAR_COLORS[i % len(AVATAR_COLORS)],
                'link': r.reseller_code.lower(),
                'earnings': f"₹{float(r.total_earnings or 0):,.0f}",
                'orders': r.total_orders or 0,
                'qr_url': request.build_absolute_uri(r.qr_image.url) if r.qr_image else None,
                'referral_link': r.referral_link,
            })
        return Response({'resellers': result})


class AdminCreateResellerView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)

        data = request.data
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()
        reseller_type = data.get('reseller_type', 'retail').strip().lower()

        if not all([name, email, password]):
            return Response({'error': 'Name, email, and password are required.'}, status=400)
        if reseller_type not in ['retail', 'influencer']:
            return Response({'error': 'Invalid reseller type.'}, status=400)
        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'An account with this email already exists.'}, status=409)

        initials = ''.join(w[0].upper() for w in name.split()[:2])
        if len(initials) < 2:
            initials = (initials + 'X')[:2]
        n = Reseller.objects.count() + 1
        code = f"{initials}{n:03d}"
        while Reseller.objects.filter(reseller_code=code).exists():
            n += 1
            code = f"{initials}{n:03d}"

        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=name,
        )

        base_url = getattr(settings, 'BASE_STORE_URL', 'https://11-11-11.shop')
        reseller = Reseller(
            user=user,
            name=name,
            phone=phone,
            reseller_code=code,
            reseller_type=reseller_type,
            referral_link=f"{base_url}/{code}-ref",
            commission_rate=100,
            is_active=True,
            plain_password=password,
        )

        if reseller_type == 'retail':
            reseller.address = data.get('store', '').strip()
            reseller.city = data.get('city', '').strip()
        else:
            reseller.platform = data.get('platform', '').strip()
            reseller.social_handle = data.get('social_handle', '').strip()

        reseller.save()

        qr_file = _generate_qr(reseller.referral_link, code)
        reseller.qr_image = qr_file
        reseller.save(update_fields=['qr_image'])

        if reseller_type == 'retail':
            store_display = reseller.address or '—'
        else:
            parts = [p for p in [reseller.platform, reseller.social_handle] if p]
            store_display = ' · '.join(parts) if parts else '—'

        qr_url = request.build_absolute_uri(reseller.qr_image.url) if reseller.qr_image else None

        return Response({
            'success': True,
            'reseller': {
                'id': reseller.id,
                'name': reseller.name,
                'email': user.email,
                'reseller_id': reseller.reseller_id,
                'reseller_code': code,
                'reseller_type': reseller_type,
                'city': reseller.city or '—',
                'store': store_display,
                'link': code.lower(),
                'earnings': '₹0',
                'orders': 0,
                'qr_url': qr_url,
                'referral_link': reseller.referral_link,
            },
        }, status=201)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()
        reseller_type = data.get('reseller_type', 'retail').strip().lower()

        if not all([name, email, password]):
            return Response({'error': 'Name, email, and password are required.'}, status=400)
        if reseller_type not in ['retail', 'influencer']:
            return Response({'error': 'Invalid reseller type.'}, status=400)
        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'An account with this email already exists.'}, status=409)

        # Generate unique reseller code from name initials
        initials = ''.join(w[0].upper() for w in name.split()[:2])
        if len(initials) < 2:
            initials = (initials + 'X')[:2]
        n = Reseller.objects.count() + 1
        code = f"{initials}{n:03d}"
        while Reseller.objects.filter(reseller_code=code).exists():
            n += 1
            code = f"{initials}{n:03d}"

        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=name,
        )

        base_url = getattr(settings, 'BASE_STORE_URL', 'https://11-11-11.shop')
        reseller = Reseller(
            user=user,
            name=name,
            phone=phone,
            reseller_code=code,
            reseller_type=reseller_type,
            referral_link=f"{base_url}/{code}-ref",
            commission_rate=100,
            is_active=False,  # pending admin approval
            plain_password=password,
        )

        if reseller_type == 'retail':
            reseller.address = data.get('address', '').strip()
            reseller.city = data.get('city', '').strip()
            reseller.state = data.get('state', '').strip()
            reseller.pincode = data.get('pincode', '').strip()
        else:
            reseller.platform = data.get('platform', '').strip()
            reseller.social_handle = data.get('social_handle', '').strip()
            reseller.follower_count = data.get('follower_count', '').strip()
            reseller.profile_url = data.get('profile_url', '').strip()

        reseller.save()

        if reseller_type == 'retail' and 'address_proof' in request.FILES:
            reseller.address_proof = request.FILES['address_proof']
            reseller.save(update_fields=['address_proof'])

        return Response({
            'success': True,
            'reseller_id': reseller.reseller_id,
            'reseller_code': reseller.reseller_code,
            'message': f"Welcome {name}! Your application (ID: {reseller.reseller_id}) is under review.",
        }, status=201)


class AdminDeleteResellerView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        try:
            reseller = Reseller.objects.select_related('user').get(pk=pk)
        except Reseller.DoesNotExist:
            return Response({'error': 'Reseller not found.'}, status=404)
        user = reseller.user
        reseller.delete()
        user.delete()
        return Response({'success': True})


class AdminUpdateCommissionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        rate = request.data.get('commission_rate')
        try:
            rate = float(rate)
            if rate < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'Invalid commission rate.'}, status=400)
        updated = Reseller.objects.filter(is_active=True).update(commission_rate=rate)
        return Response({'success': True, 'updated_resellers': updated, 'commission_rate': rate})


class AdminChangePasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        new_password = request.data.get('new_password', '').strip()
        confirm = request.data.get('confirm_password', '').strip()
        if not new_password:
            return Response({'error': 'New password is required.'}, status=400)
        if new_password != confirm:
            return Response({'error': 'Passwords do not match.'}, status=400)
        if len(new_password) < 6:
            return Response({'error': 'Password must be at least 6 characters.'}, status=400)
        from decouple import config as env
        admin_user = env('ADMIN_USERNAME', default='111111.admin')
        user, _ = User.objects.get_or_create(username=admin_user, defaults={'email': ''})
        user.set_password(new_password)
        user.save()
        return Response({'success': True, 'message': 'Password updated. Restart server to also update .env.'})


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from decouple import config as env
        admin_user = env('ADMIN_USERNAME', default='')
        admin_pass = env('ADMIN_PASSWORD', default='')
        if not admin_user or not admin_pass:
            return Response({'error': 'Admin credentials not configured on server.'}, status=503)
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if username == admin_user and password == admin_pass:
            return Response({'success': True})
        return Response({'error': 'Invalid credentials.'}, status=401)


class AdminApproveApplicationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        from .models import ResellerApplication
        try:
            app = ResellerApplication.objects.get(pk=pk, status='pending')
        except ResellerApplication.DoesNotExist:
            return Response({'error': 'Application not found or already processed.'}, status=404)

        password = 'Res@' + ''.join(random.choices(string.digits, k=6))
        phone_digits = ''.join(filter(str.isdigit, app.phone))
        email = f'{phone_digits}@reseller.local'
        if User.objects.filter(email__iexact=email).exists():
            email = f'{phone_digits}_{pk}@reseller.local'

        initials = ''.join(w[0].upper() for w in app.name.split()[:2])
        if len(initials) < 2:
            initials = (initials + 'X')[:2]
        n = Reseller.objects.count() + 1
        code = f"{initials}{n:03d}"
        while Reseller.objects.filter(reseller_code=code).exists():
            n += 1
            code = f"{initials}{n:03d}"

        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=app.name,
        )

        base_url = getattr(settings, 'BASE_STORE_URL', 'http://127.0.0.1:8000')
        referral_link = f"{base_url}/{code}-ref"

        reseller = Reseller(
            user=user,
            name=app.name,
            phone=app.phone,
            reseller_code=code,
            reseller_type='retail',
            referral_link=referral_link,
            commission_rate=100,
            is_active=True,
            address=app.store_address,
            plain_password=password,
        )
        reseller.save()

        qr_file = _generate_qr(referral_link, code)
        reseller.qr_image = qr_file
        reseller.save(update_fields=['qr_image'])

        app.status = 'approved'
        app.save()

        qr_url = request.build_absolute_uri(reseller.qr_image.url) if reseller.qr_image else None
        color = AVATAR_COLORS[Reseller.objects.count() % len(AVATAR_COLORS)]

        return Response({
            'success': True,
            'reseller': {
                'id': reseller.id,
                'name': reseller.name,
                'store': app.store_name or '—',
                'city': '—',
                'earnings': '₹0',
                'orders': 0,
                'link': code.lower(),
                'type': 'retail',
                'reseller_id': reseller.reseller_id,
                'reseller_code': code,
                'referral_link': referral_link,
                'qr_url': qr_url,
                'color': color,
                'is_active': True,
            },
            'credentials': {
                'phone': app.phone,
                'password': password,
            },
        }, status=201)


class ApplyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from .models import ResellerApplication
        data = request.data
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        if not name or not phone:
            return Response({'error': 'Name and phone are required.'}, status=400)
        app = ResellerApplication.objects.create(
            name=name,
            phone=phone,
            whatsapp=data.get('whatsapp', '').strip(),
            email=data.get('email', '').strip(),
            store_name=data.get('store_name', '').strip(),
            store_address=data.get('store_address', '').strip(),
            outlet_type=data.get('outlet_type', '').strip(),
            bank_upi=data.get('bank_upi', '').strip(),
        )
        return Response({
            'success': True,
            'id': app.id,
            'message': f"Application submitted! We'll review and contact you on {phone} within 48 hours.",
        }, status=201)


class AdminPayoutsView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """List all resellers with their cumulative earnings, paid, and pending."""
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        from store.models import Order
        from django.db.models import Sum as DSum

        resellers = Reseller.objects.filter(is_active=True).order_by('name')
        result = []
        for r in resellers:
            total_earned = float(
                Order.objects.filter(reseller=r)
                .aggregate(v=DSum('commission_amount'))['v'] or 0
            )
            total_paid = float(
                ResellerPayout.objects.filter(reseller=r, status='paid')
                .aggregate(v=DSum('amount'))['v'] or 0
            )
            pending = round(total_earned - total_paid, 2)

            history = []
            for p in ResellerPayout.objects.filter(reseller=r, status='paid').order_by('-paid_at')[:10]:
                history.append({
                    'id':          p.id,
                    'amount':      float(p.amount),
                    'period':      p.period,
                    'payment_mode': p.payment_mode,
                    'payment_reference': p.payment_reference,
                    'screenshot_url': request.build_absolute_uri(p.screenshot.url) if p.screenshot else None,
                    'notes':       p.notes,
                    'paid_at':     p.paid_at.strftime('%d %b %Y, %I:%M %p') if p.paid_at else '—',
                })

            result.append({
                'id':           r.id,
                'name':         r.name,
                'phone':        r.phone,
                'reseller_code': r.reseller_code,
                'reseller_id':  r.reseller_id,
                'total_earned': total_earned,
                'total_paid':   total_paid,
                'pending':      pending,
                'color':        AVATAR_COLORS[list(resellers).index(r) % len(AVATAR_COLORS)],
                'history':      history,
            })
        return Response({'resellers': result})

    def post(self, request, pk):
        """Record a payment for a reseller."""
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        try:
            reseller = Reseller.objects.get(pk=pk, is_active=True)
        except Reseller.DoesNotExist:
            return Response({'error': 'Reseller not found.'}, status=404)

        amount = request.data.get('amount')
        payment_mode = request.data.get('payment_mode', '').strip()
        payment_reference = request.data.get('payment_reference', '').strip()
        period = request.data.get('period', '').strip()
        notes = request.data.get('notes', '').strip()
        screenshot = request.FILES.get('screenshot')

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount.'}, status=400)
        if payment_mode not in ('upi', 'bank_transfer', 'cash'):
            return Response({'error': 'payment_mode must be upi, bank_transfer, or cash.'}, status=400)

        payout = ResellerPayout.objects.create(
            reseller=reseller,
            amount=amount,
            status='paid',
            period=period,
            payment_mode=payment_mode,
            payment_reference=payment_reference,
            notes=notes,
            paid_at=timezone.now(),
        )
        if screenshot:
            payout.screenshot = screenshot
            payout.save(update_fields=['screenshot'])

        screenshot_url = request.build_absolute_uri(payout.screenshot.url) if payout.screenshot else None
        return Response({
            'success': True,
            'payout': {
                'id': payout.id,
                'amount': float(payout.amount),
                'period': payout.period,
                'payment_mode': payout.payment_mode,
                'payment_reference': payout.payment_reference,
                'screenshot_url': screenshot_url,
                'notes': payout.notes,
                'paid_at': payout.paid_at.strftime('%d %b %Y, %I:%M %p'),
            },
        }, status=201)


class AdminApplicationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        from .models import ResellerApplication
        apps = ResellerApplication.objects.all()
        result = [{
            'id': a.id,
            'name': a.name,
            'phone': a.phone,
            'whatsapp': a.whatsapp,
            'email': a.email,
            'store_name': a.store_name,
            'store_address': a.store_address,
            'outlet_type': a.outlet_type,
            'bank_upi': a.bank_upi,
            'status': a.status,
            'applied_at': a.applied_at.strftime('%d %b %Y, %I:%M %p'),
        } for a in apps]
        return Response({
            'applications': result,
            'pending_count': sum(1 for a in result if a['status'] == 'pending'),
        })


class AdminApplicationActionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        if not _check_admin(request):
            return Response({'error': 'Unauthorized.'}, status=401)
        from .models import ResellerApplication
        try:
            app = ResellerApplication.objects.get(pk=pk)
        except ResellerApplication.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        action = request.data.get('action', '')
        if action == 'approve':
            app.status = 'approved'
        elif action == 'reject':
            app.status = 'rejected'
        else:
            return Response({'error': 'Invalid action. Use approve or reject.'}, status=400)
        app.save()
        return Response({'success': True, 'status': app.status})
