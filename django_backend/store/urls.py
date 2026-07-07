from django.urls import path
from . import views

urlpatterns = [
    path('place-order/', views.PlaceOrderView.as_view(), name='place-order'),
    path('products/', views.ProductsView.as_view(), name='products'),
    path('reseller-sales/', views.ResellerSalesView.as_view(), name='reseller-sales'),
]
