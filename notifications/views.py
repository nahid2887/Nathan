from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Notification
from .serializers import NotificationSerializer, RegisterFCMTokenSerializer, NotificationSettingsSerializer



class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Notifications",
        operation_description="Retrieve a list of notifications for the authenticated user.",
        tags=['Notifications'],
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
        tags=['Notifications'],
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
        tags=['Notifications'],
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
        tags=['Notifications'],
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


class RegisterFCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Register FCM Device Token",
        operation_description="Save the Firebase Cloud Messaging device token for the authenticated user.",
        tags=['Notifications'],
        request_body=RegisterFCMTokenSerializer,
        responses={
            200: openapi.Response(
                description="Token registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid payload"
        }
    )
    def post(self, request):
        serializer = RegisterFCMTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        fcm_token = serializer.validated_data["fcm_token"]
        user = request.user
        user.fcm_token = fcm_token
        user.save(update_fields=['fcm_token'])

        return Response({
            "success": True,
            "message": "FCM device token registered successfully."
        }, status=status.HTTP_200_OK)


class NotificationSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Push Notification Settings",
        operation_description="Retrieve push notification preferences and radius of the authenticated user.",
        tags=['Notifications'],
        responses={200: NotificationSettingsSerializer()}
    )
    def get(self, request):
        serializer = NotificationSettingsSerializer(request.user)
        return Response({
            "success": True,
            "settings": serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update Push Notification Settings",
        operation_description="Update push notification preferences and radius of the authenticated user using PATCH.",
        tags=['Notifications'],
        request_body=NotificationSettingsSerializer,
        responses={
            200: openapi.Response(
                description="Settings updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "settings": openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Invalid payload"
        }
    )
    def patch(self, request):
        serializer = NotificationSettingsSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({
            "success": True,
            "message": "Notification settings updated successfully.",
            "settings": serializer.data
        }, status=status.HTTP_200_OK)


