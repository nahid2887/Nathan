from django.urls import path
from .views import (
    RegisterView,
    ChangePasswordView,
    LoginView,
    ProfileView,
    ForgotPasswordView,
    VerifyOTPView,
    ResetPasswordView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path(
        'register/',
        RegisterView.as_view(),
        name='register'
    ),

    path(
        'login/',
        LoginView.as_view(),
        name='login'
    ),

    path(
        'refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    path(
        'change-password/',
        ChangePasswordView.as_view(),
        name='change_password'
    ),

    path(
        'profile/',
        ProfileView.as_view(),
        name='profile'
    ),

    path(
        'forgot-password/',
        ForgotPasswordView.as_view(),
        name='forgot_password'
    ),

    path(
        'verify-otp/',
        VerifyOTPView.as_view(),
        name='verify_otp'
    ),

    path(
        'reset-password/',
        ResetPasswordView.as_view(),
        name='reset_password'
    ),
]