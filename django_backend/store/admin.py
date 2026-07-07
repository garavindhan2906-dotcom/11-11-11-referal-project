from django.contrib import admin
from .models import Product, Customer, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'intent', 'price', 'for_gender', 'emoji', 'in_stock']
    list_filter = ['for_gender', 'in_stock']
    list_editable = ['price', 'in_stock']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['unit_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'reseller', 'total_amount', 'commission_amount', 'status', 'created_at']
    list_filter = ['status', 'reseller', 'created_at']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at']
    search_fields = ['order_number', 'customer__name', 'customer__email']
    date_hierarchy = 'created_at'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'referred_by', 'order_count', 'created_at']
    list_filter = ['referred_by']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at']

    def order_count(self, obj):
        return obj.orders.count()
    order_count.short_description = 'Orders'
