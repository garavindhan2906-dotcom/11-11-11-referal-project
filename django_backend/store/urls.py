from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.ProductsView.as_view(), name="products"),
    path("products/create/", views.ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/update/", views.ProductUpdateView.as_view(), name="product-update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product-delete"),
    path("place-order/", views.PlaceOrderView.as_view(), name="place-order"),
    path("reseller-sales/", views.ResellerSalesView.as_view(), name="reseller-sales"),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
]
