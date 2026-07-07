from django.contrib import admin
from django.db.models import Sum, Count
from .models import Reseller, ResellerPayout, QRScan


@admin.register(Reseller)
class ResellerAdmin(admin.ModelAdmin):
    list_display = ['reseller_id', 'name', 'reseller_type', 'reseller_code', 'user_email', 'is_active', 'total_orders', 'total_earned', 'created_at']
    list_filter = ['reseller_type', 'is_active']
    search_fields = ['name', 'reseller_code', 'reseller_id', 'user__email']
    readonly_fields = ['reseller_id', 'created_at', 'referral_link', 'qr_image']
    list_editable = ['is_active']
    fieldsets = [
        ('Account', {'fields': ['user', 'name', 'phone', 'reseller_type', 'reseller_id', 'reseller_code', 'referral_link', 'qr_image', 'commission_rate', 'is_active', 'created_at']}),
        ('Retail Details', {'fields': ['address', 'city', 'state', 'pincode', 'address_proof'], 'classes': ['collapse']}),
        ('Influencer Details', {'fields': ['platform', 'social_handle', 'follower_count', 'profile_url'], 'classes': ['collapse']}),
    ]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def total_orders(self, obj):
        return obj.orders.count()
    total_orders.short_description = 'Orders'

    def total_earned(self, obj):
        val = obj.orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        return f"₹{val:,.0f}"
    total_earned.short_description = 'Earned'


@admin.register(ResellerPayout)
class ResellerPayoutAdmin(admin.ModelAdmin):
    list_display = ['reseller', 'period', 'amount', 'status', 'requested_at', 'paid_at']
    list_filter = ['status', 'reseller']
    list_editable = ['status']
    readonly_fields = ['requested_at']


@admin.register(QRScan)
class QRScanAdmin(admin.ModelAdmin):
    list_display = ['reseller', 'scanned_at', 'ip_address']
    list_filter = ['reseller']
    readonly_fields = ['scanned_at']
    date_hierarchy = 'scanned_at'
