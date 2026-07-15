from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 
            'is_read', 'event', 'recommendation', 'looking_for', 
            'alert', 'created_at'
        ]
        read_only_fields = fields


class RegisterFCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(required=True, allow_blank=True)

