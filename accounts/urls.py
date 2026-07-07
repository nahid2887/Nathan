from django.urls import path
from .views import (
    RegisterView,
    ChangePasswordView,
    LoginView,
    ProfileView,
    ForgotPasswordView,
    VerifyOTPView,
    ResetPasswordView,
    NearbyUsersView,
    SendFriendRequestView,
    IncomingFriendRequestsView,
    AcceptFriendRequestView,
    RejectFriendRequestView,
    FriendsListView,
    RemoveFriendView,
    PlanListView,
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

    path(
        'users/nearby/',
        NearbyUsersView.as_view(),
        name='nearby_users'
    ),

    # Friends endpoints
    path(
        'friends/requests/send/',
        SendFriendRequestView.as_view(),
        name='friend_request_send'
    ),
    path(
        'friends/requests/',
        IncomingFriendRequestsView.as_view(),
        name='friend_requests_incoming'
    ),
    path(
        'friends/requests/<int:request_id>/accept/',
        AcceptFriendRequestView.as_view(),
        name='friend_request_accept'
    ),
    path(
        'friends/requests/<int:request_id>/reject/',
        RejectFriendRequestView.as_view(),
        name='friend_request_reject'
    ),
    path(
        'friends/',
        FriendsListView.as_view(),
        name='friends_list'
    ),
    path(
        'friends/<int:friend_id>/',
        RemoveFriendView.as_view(),
        name='friend_remove'
    ),
    path(
        'plans/',
        PlanListView.as_view(),
        name='plans_list'
    ),
]