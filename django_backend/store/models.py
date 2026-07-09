from django.db import models
from django.utils import timezone


class Product(models.Model):
    GENDER_CHOICES = [('male', 'For Him'), ('female', 'For Her'), ('combo', 'Combo')]
    name = models.CharField(max_length=200)
    intent = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    for_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    emoji = models.CharField(max_length=10, blank=True)
    in_stock = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    video = models.FileField(upload_to='products/videos/', null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_for_gender_display()})"

    class Meta:
        ordering = ['for_gender', 'name']


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    referred_by = models.ForeignKey(
        'resellers.Reseller',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='customers',
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        ordering = ['-created_at']


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    reseller = models.ForeignKey(
        'resellers.Reseller',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"#{self.order_number} — {self.customer.name}"

    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ×{self.quantity}"
