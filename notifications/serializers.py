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


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        from django.contrib.auth import get_user_model
        model = get_user_model()
        fields = [
            'notify_new_posts',
            'notify_marketplace',
            'notify_business',
            'notify_events',
            'distance_radius'
        ]

    def validate_distance_radius(self, value):
        if value is not None:
            if value < 0.5 or value > 10.0:
                raise serializers.ValidationError("Coverage area must be between 0.5km and 10.0km.")
        return value



