from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Notifications",
        operation_description="Retrieve a list of notifications for the authenticated user.",
        responses={
            200: openapi.Response(
                description="List of notifications",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "unread_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "notifications": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        unread_count = notifications.filter(is_read=False).count()
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            "success": True,
            "unread_count": unread_count,
            "notifications": serializer.data
        }, status=status.HTTP_200_OK)

class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Unread Notification Count",
        operation_description="Get the count of unread notifications for the authenticated user.",
        responses={
            200: openapi.Response(
                description="Unread count",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "unread_count": openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )
    def get(self, request):
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            "success": True,
            "unread_count": unread_count
        }, status=status.HTTP_200_OK)

class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark Notification as Read",
        operation_description="Mark a specific notification as read.",
        responses={
            200: openapi.Response(
                description="Notification marked as read successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "unread_count": openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            404: "Notification not found"
        }
    )
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            if not notification.is_read:
                notification.is_read = True
                notification.save()
            
            unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
            return Response({
                "success": True,
                "message": "Notification marked as read.",
                "unread_count": unread_count
            }, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({
                "success": False,
                "message": "Notification not found."
            }, status=status.HTTP_404_NOT_FOUND)

class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark All Notifications as Read",
        operation_description="Mark all unread notifications of the authenticated user as read.",
        responses={
            200: openapi.Response(
                description="All notifications marked as read",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "unread_count": openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({
            "success": True,
            "message": "All notifications marked as read.",
            "unread_count": 0
        }, status=status.HTTP_200_OK)
