from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Reseller(models.Model):
    TYPE_CHOICES = [('retail', 'Retail Reseller'), ('influencer', 'Influencer Reseller')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reseller')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    reseller_code = models.CharField(max_length=20, unique=True)
    reseller_id = models.CharField(max_length=20, unique=True, blank=True)
    reseller_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='retail')
    referral_link = models.URLField(max_length=500)
    qr_image = models.ImageField(upload_to='qrcodes/', blank=True)
    commission_rate = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Retail-specific fields
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    address_proof = models.FileField(upload_to='address_proofs/', blank=True, null=True)

    # Influencer-specific fields
    platform = models.CharField(max_length=50, blank=True)
    social_handle = models.CharField(max_length=200, blank=True)
    follower_count = models.CharField(max_length=50, blank=True)
    profile_url = models.URLField(max_length=500, blank=True)

    def save(self, *args, **kwargs):
        if not self.reseller_id:
            prefix = 'RTSE' if self.reseller_type == 'retail' else 'INSE'
            count = Reseller.objects.filter(reseller_type=self.reseller_type).count() + 1
            self.reseller_id = f"{prefix}-{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.reseller_id or self.reseller_code})"

    class Meta:
        ordering = ['name']


class ResellerPayout(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('paid', 'Paid'), ('processing', 'Processing')]
    reseller = models.ForeignKey(Reseller, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    period = models.CharField(max_length=50)
    dates = models.CharField(max_length=100, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.reseller.name} — ₹{self.amount} ({self.period})"

    class Meta:
        ordering = ['-requested_at']


class QRScan(models.Model):
    reseller = models.ForeignKey(Reseller, on_delete=models.CASCADE, related_name='qr_scans')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    scanned_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Scan — {self.reseller.name} at {self.scanned_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-scanned_at']
