from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('read-all/', MarkAllNotificationsReadView.as_view(), name='mark-all-notifications-read'),
]
