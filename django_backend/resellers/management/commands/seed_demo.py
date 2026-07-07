import random
from datetime import datetime, timedelta
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware

from resellers.models import Reseller, ResellerPayout, QRScan
from store.models import Customer, Order, OrderItem, Product

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# ─────────────────────────────────────────────────────────────────────────────
RESELLERS_CONFIG = [
    {
        'name': 'Aravind',
        'email': 'aravind@111-11-11.shop',
        'password': 'Aravind@1111',
        'code': 'AV001',
        'phone': '+91 98765 43210',
        'reseller_type': 'retail',
        'address': '14, Gandhi Nagar, 2nd Cross Street',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'pincode': '600020',
        'order_count': 32,
        'customer_count': 16,
        'payouts': [
            ('Jan 2025', '1 – 31 Jan', 2800, '2025-02-05'),
            ('Feb 2025', '1 – 28 Feb', 2400, '2025-03-05'),
            ('Mar 2025', '1 – 31 Mar', 2900, '2025-04-05'),
            ('Apr 2025', '1 – 30 Apr', 3200, '2025-05-05'),
            ('May 2025', '1 – 31 May', 3300, '2025-06-05'),
            ('Jun 2025 (pending)', '1 – 30 Jun', 3200, None),
        ],
    },
    {
        'name': 'Sibi',
        'email': 'sibi@111-11-11.shop',
        'password': 'Sibi@1111',
        'code': 'SB001',
        'phone': '+91 87654 32109',
        'reseller_type': 'influencer',
        'platform': 'Instagram',
        'social_handle': '@sibi.manifestation',
        'follower_count': '48,200',
        'profile_url': 'https://instagram.com/sibi.manifestation',
        'order_count': 24,
        'customer_count': 12,
        'payouts': [
            ('Feb 2025', '1 – 28 Feb', 2300, '2025-03-05'),
            ('Mar 2025', '1 – 31 Mar', 2600, '2025-04-05'),
            ('Apr 2025', '1 – 30 Apr', 2400, '2025-05-05'),
            ('May 2025', '1 – 31 May', 2800, '2025-06-05'),
            ('Jun 2025 (pending)', '1 – 30 Jun', 2400, None),
        ],
    },
    {
        'name': 'Bhupan',
        'email': 'bhupan@111-11-11.shop',
        'password': 'Bhupan@1111',
        'code': 'BH001',
        'phone': '+91 76543 21098',
        'reseller_type': 'retail',
        'address': '22, MG Road, Koramangala',
        'city': 'Bengaluru',
        'state': 'Karnataka',
        'pincode': '560034',
        'order_count': 38,
        'customer_count': 18,
        'payouts': [
            ('Jan 2025', '1 – 31 Jan', 3200, '2025-02-05'),
            ('Feb 2025', '1 – 28 Feb', 3600, '2025-03-05'),
            ('Mar 2025', '1 – 31 Mar', 3400, '2025-04-05'),
            ('Apr 2025', '1 – 30 Apr', 3800, '2025-05-05'),
            ('May 2025', '1 – 31 May', 4100, '2025-06-05'),
            ('Jun 2025 (pending)', '1 – 30 Jun', 3800, None),
        ],
    },
]

PRODUCTS_DATA = [
    ('KLEOMA',        'Love & Attraction',        1234, 'male',   '🌹'),
    ('KLINFON',       'Relaxation & Calm',         1234, 'male',   '🌿'),
    ('MYSTRA',        'Financial Clarity',         1234, 'male',   '⚖️'),
    ('SHREEMSRI',     'Wealth & Prosperity',       1234, 'male',   '👑'),
    ('SUKCE',         'Success & Achievement',     1234, 'male',   '🏆'),
    ('KAMAVYA',       'Attraction & Love',         1234, 'female', '🌸'),
    ('KLINFON (Her)', 'Relaxation & Calm',         1234, 'female', '🌙'),
    ('HREMAAN',       'Financial Clarity',         1234, 'female', '✨'),
    ('SHRIVAA',       'Wealth & Prosperity',       1234, 'female', '💛'),
    ('YCNEX',         'Confidence & Success',      1234, 'female', '⭐'),
    ('KLINFON Combo', 'Relaxation — Him & Her',   2345, 'combo',  '🤍'),
    ('Love Combo',    'Love & Attraction — Him & Her', 2345, 'combo', '💕'),
]

CUSTOMER_POOL = [
    'Meera Nair', 'Ananya Iyer', 'Rohit Verma', 'Kiran Shah', 'Divya Pillai',
    'Preethi Raj', 'Sanjay Malhotra', 'Arnav Gupta', 'Riya Sharma', 'Vikram Nair',
    'Sneha Patel', 'Arjun Kumar', 'Pooja Menon', 'Raj Agarwal', 'Nisha Reddy',
    'Deepak Singh', 'Kavya Bhat', 'Rahul Joshi', 'Shreya Pillai', 'Suresh Kumar',
    'Priya Iyer', 'Ramesh Rao', 'Geetha Krishnan', 'Lakshmi Devi', 'Mohan Das',
    'Sita Ram', 'Vivek Oberoi', 'Neha Sharma', 'Akash Gupta', 'Sumitra Devi',
    'Karthik Raja', 'Bhavana Menon', 'Pradeep Kumar', 'Anjali Singh', 'Mithun Roy',
    'Pallavi Iyer', 'Ganesh Murthy', 'Leela Thomas', 'Harish Babu', 'Madhuri Nair',
    'Srinivas Rao', 'Naveen Kumar', 'Rajan Pillai', 'Mamtha Mohandas', 'Biju Menon',
    'Saranya Rao', 'Chandru Pillai', 'Vijay Menon', 'Roshan Thomas', 'Aditi Shah',
]

STATUSES = ['delivered'] * 7 + ['processing'] * 2 + ['pending'] * 1


# ─────────────────────────────────────────────────────────────────────────────
def _make_qr(code, base_url):
    if not HAS_QRCODE:
        return None
    try:
        url = f"{base_url}/{code}-ref"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1C1914', back_color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception as e:
        return None


def _dt(date_str):
    return make_aware(datetime.strptime(date_str, '%Y-%m-%d').replace(hour=10))


# ─────────────────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = 'Seed demo data: 3 resellers (Aravind, Sibi, Bhupan) with orders, customers, QR scans, payouts'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete all existing data before seeding')

    def handle(self, *args, **options):
        if options['flush']:
            self._flush()

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  ┌─────────────────────────────────────┐'))
        self.stdout.write(self.style.HTTP_INFO('  │   11:11:11 · EVOXU  Demo Seeder     │'))
        self.stdout.write(self.style.HTTP_INFO('  └─────────────────────────────────────┘'))
        self.stdout.write('')

        products = self._seed_products()

        from django.conf import settings
        base_url = getattr(settings, 'BASE_STORE_URL', 'https://11-11-11.shop')

        for cfg in RESELLERS_CONFIG:
            self._seed_reseller(cfg, products, base_url)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('  ✅  Demo data seeded!\n'))
        self.stdout.write('  ┌──────────────┬──────────────────────────────┬────────────────┐')
        self.stdout.write('  │   Reseller   │            Email             │    Password    │')
        self.stdout.write('  ├──────────────┼──────────────────────────────┼────────────────┤')
        for r in RESELLERS_CONFIG:
            self.stdout.write(f"  │ {r['name']:<12} │ {r['email']:<28} │ {r['password']:<14} │")
        self.stdout.write('  └──────────────┴──────────────────────────────┴────────────────┘')
        self.stdout.write('')
        self.stdout.write('  Admin panel : http://localhost:8000/admin/')
        self.stdout.write('  Login API   : http://localhost:8000/api/reseller/login/')
        self.stdout.write('')

    # ── helpers ────────────────────────────────────────────────────────────────

    def _flush(self):
        self.stdout.write('  Flushing existing data...')
        emails = [r['email'] for r in RESELLERS_CONFIG]
        QRScan.objects.filter(reseller__user__username__in=emails).delete()
        OrderItem.objects.filter(order__reseller__user__username__in=emails).delete()
        Order.objects.filter(reseller__user__username__in=emails).delete()
        Customer.objects.filter(referred_by__user__username__in=emails).delete()
        ResellerPayout.objects.filter(reseller__user__username__in=emails).delete()
        Reseller.objects.filter(user__username__in=emails).delete()
        User.objects.filter(username__in=emails).delete()
        Product.objects.all().delete()
        self.stdout.write('  ✓ Flushed\n')

    def _seed_products(self):
        if Product.objects.exists():
            self.stdout.write('  ✓ Products already exist — skipping')
            return list(Product.objects.all())
        products = []
        for name, intent, price, gender, emoji in PRODUCTS_DATA:
            p = Product.objects.create(
                name=name,
                intent=intent,
                price=price,
                for_gender=gender,
                emoji=emoji,
                description=f"Sacred manifestation oil for {intent.lower()}.",
            )
            products.append(p)
        self.stdout.write(f'  ✓ Seeded {len(products)} products')
        return products

    def _seed_reseller(self, cfg, products, base_url):
        if User.objects.filter(username=cfg['email']).exists():
            self.stdout.write(f"  ✓ {cfg['name']} already exists — skipping")
            return

        # Django user
        user = User.objects.create_user(
            username=cfg['email'],
            email=cfg['email'],
            password=cfg['password'],
            first_name=cfg['name'],
        )

        referral_link = f"{base_url}/{cfg['code']}-ref"
        rtype = cfg.get('reseller_type', 'retail')
        reseller = Reseller(
            user=user,
            name=cfg['name'],
            phone=cfg['phone'],
            reseller_code=cfg['code'],
            reseller_type=rtype,
            referral_link=referral_link,
            commission_rate=100,
            is_active=True,
        )
        if rtype == 'retail':
            reseller.address = cfg.get('address', '')
            reseller.city = cfg.get('city', '')
            reseller.state = cfg.get('state', '')
            reseller.pincode = cfg.get('pincode', '')
        else:
            reseller.platform = cfg.get('platform', '')
            reseller.social_handle = cfg.get('social_handle', '')
            reseller.follower_count = cfg.get('follower_count', '')
            reseller.profile_url = cfg.get('profile_url', '')
        reseller.save()

        # QR code image
        qr_bytes = _make_qr(cfg['code'], base_url)
        if qr_bytes:
            reseller.qr_image.save(f"{cfg['code']}.png", ContentFile(qr_bytes), save=True)
        else:
            self.stdout.write(f"  ⚠  QR image skipped for {cfg['name']} (install qrcode + Pillow)")

        # Customers
        now = timezone.now()
        names = random.sample(CUSTOMER_POOL, cfg['customer_count'])
        prefix = cfg['code'].lower()
        customers = []
        for cname in names:
            slug = cname.lower().replace(' ', '.')
            email = f"{prefix}.{slug}@demo.shop"
            days_back = random.randint(60, 400)
            joined = now - timedelta(days=days_back, hours=random.randint(0, 23))
            c, _ = Customer.objects.get_or_create(
                email=email,
                defaults={'name': cname, 'referred_by': reseller, 'created_at': joined},
            )
            customers.append(c)

        # Orders — spread across last 12 months
        orders_created = 0
        for _ in range(cfg['order_count']):
            customer = random.choice(customers)
            product = random.choice(products)
            days_ago = random.randint(0, 365)
            order_date = now - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            order_num = f"{cfg['code']}-{(Order.objects.count() + 1):04d}"
            order = Order(
                order_number=order_num,
                customer=customer,
                reseller=reseller,
                total_amount=product.price,
                commission_amount=100,
                status=random.choice(STATUSES),
                created_at=order_date,
            )
            order.save()
            OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=product.price)
            orders_created += 1

        # QR scans — 6–10× order count
        scan_count = cfg['order_count'] * random.randint(6, 10)
        scans = []
        for _ in range(scan_count):
            days_ago = random.randint(0, 365)
            scan_date = now - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            scans.append(QRScan(
                reseller=reseller,
                scanned_at=scan_date,
                ip_address=f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            ))
        QRScan.objects.bulk_create(scans)

        # Payouts
        for period, dates, amount, paid_date_str in cfg['payouts']:
            paid_at = _dt(paid_date_str) if paid_date_str else None
            ResellerPayout.objects.create(
                reseller=reseller,
                amount=amount,
                status='paid' if paid_at else 'pending',
                period=period,
                dates=dates,
                paid_at=paid_at,
                requested_at=paid_at or now,
            )

        total_earn = orders_created * 100
        total_scans = len(scans)
        self.stdout.write(
            f"  ✓ {cfg['name']:<10}  {orders_created} orders · {cfg['customer_count']} customers"
            f" · {total_scans} QR scans · ₹{total_earn:,} earned"
        )
