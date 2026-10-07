"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from catalog.urls import direct_router as catalog_direct_router
from users.views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MerchantPasswordRecoveryConfirmView,
    MerchantPasswordRecoveryRequestView,
    RefreshView,
    SuperAdminAdministrativeResetConfirmView,
    SuperAdminAdministrativeResetRequestView,
    SuperAdminCreateMerchantView,
    SuperAdminLoginView,
    SuperAdminSelfRecoveryConfirmView,
    SuperAdminSelfRecoveryRequestView,
)
from customers.views import CustomerOrderCancellationView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/v1/auth/super-admin/login/', SuperAdminLoginView.as_view(), name='auth-super-admin-login'),
    path('api/v1/super-admin/merchants/', SuperAdminCreateMerchantView.as_view(), name='super-admin-merchant-create'),
    path('api/v1/auth/super-admin/recovery/', SuperAdminSelfRecoveryRequestView.as_view(), name='auth-super-admin-recovery-request'),
    path('api/v1/auth/super-admin/recovery/confirm/', SuperAdminSelfRecoveryConfirmView.as_view(), name='auth-super-admin-recovery-confirm'),
    path('api/v1/auth/super-admin/password-reset-requests/', SuperAdminAdministrativeResetRequestView.as_view(), name='auth-super-admin-reset-request'),
    path('api/v1/auth/super-admin/password-reset-requests/confirm/', SuperAdminAdministrativeResetConfirmView.as_view(), name='auth-super-admin-reset-confirm'),
    path('api/v1/auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('api/v1/auth/merchant-password-recovery/', MerchantPasswordRecoveryRequestView.as_view(), name='auth-merchant-password-recovery-request'),
    path('api/v1/auth/merchant-password-recovery/confirm/', MerchantPasswordRecoveryConfirmView.as_view(), name='auth-merchant-password-recovery-confirm'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/v1/auth/refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('api/v1/shops/', include('shops.urls')),
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/customers/', include('customers.urls')),
    path('api/v1/customer/orders/<int:order_id>/cancellation/', CustomerOrderCancellationView.as_view(), name='customer-order-cancellation'),
    path('api/v1/cart/', include('cart.urls')),
    path('api/v1/', include('orders.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/master-products/', include((catalog_direct_router.urls, 'master-products-direct'))),
]

