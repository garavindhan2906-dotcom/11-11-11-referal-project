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
    path('apply/', views.ApplyView.as_view(), name='reseller-apply'),
    path('admin-applications/', views.AdminApplicationsView.as_view(), name='admin-applications'),
    path('admin-applications/<int:pk>/action/', views.AdminApplicationActionView.as_view(), name='admin-application-action'),
    path('admin-applications/<int:pk>/approve-create/', views.AdminApproveApplicationView.as_view(), name='admin-approve-application'),
    path('admin-delete/<int:pk>/', views.AdminDeleteResellerView.as_view(), name='admin-delete-reseller'),
    path('admin-payouts/', views.AdminPayoutsView.as_view(), name='admin-payouts'),
    path('admin-payouts/<int:pk>/pay/', views.AdminPayoutsView.as_view(), name='admin-pay'),
    path('admin-commission/', views.AdminUpdateCommissionView.as_view(), name='admin-commission'),
    path('admin-change-password/', views.AdminChangePasswordView.as_view(), name='admin-change-password'),
]
