from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Alert

User = get_user_model()

class AlertCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class AlertSerializer(serializers.ModelSerializer):
    creator = AlertCreatorSerializer(read_only=True)
    type = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    hours_ago = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id', 'creator', 'title', 'content', 'location_name', 'latitude', 'longitude',
            'alert_type', 'alert_level', 'privacy', 'photo', 'is_anonymous',
            'created_at', 'updated_at', 'type', 'distance_km', 'hours_ago'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at', 'type', 'distance_km', 'hours_ago']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data['creator'] = None
        return data

    def get_type(self, obj):
        return 'alert'

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            user = request.user
            if user.latitude is not None and user.longitude is not None:
                if obj.latitude is not None and obj.longitude is not None:
                    from events.views import haversine_distance
                    dist = haversine_distance(user.latitude, user.longitude, obj.latitude, obj.longitude)
                    return round(dist, 2)
        return None

    def get_hours_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        return round(diff.total_seconds() / 3600, 1)

class AlertWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'title', 'content', 'location_name', 'latitude', 'longitude',
            'alert_type', 'alert_level', 'privacy', 'photo', 'is_anonymous'
        ]

    def to_representation(self, instance):
        return AlertSerializer(instance, context=self.context).data

