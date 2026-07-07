from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='reseller-login'),
    path('dashboard/', views.DashboardView.as_view(), name='reseller-dashboard'),
    path('orders/', views.OrdersView.as_view(), name='reseller-orders'),
    path('earnings/', views.EarningsView.as_view(), name='reseller-earnings'),
    path('customers/', views.CustomersView.as_view(), name='reseller-customers'),
    path('referrals/', views.ReferralsView.as_view(), name='reseller-referrals'),
    path('notifications/', views.NotificationsView.as_view(), name='reseller-notifications'),
    path('track-scan/', views.TrackScanView.as_view(), name='track-scan'),
    path('register/', views.RegisterView.as_view(), name='reseller-register'),
    path('admin-list/', views.AdminListResellersView.as_view(), name='admin-list'),
    path('admin-create/', views.AdminCreateResellerView.as_view(), name='admin-create'),
]
