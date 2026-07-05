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

    class Meta:
        model = Alert
        fields = [
            'id', 'creator', 'content', 'location_name', 'latitude', 'longitude',
            'alert_type', 'alert_level', 'privacy', 'created_at', 'updated_at', 'type', 'distance_km'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at', 'type', 'distance_km']

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

class AlertWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'content', 'location_name', 'latitude', 'longitude',
            'alert_type', 'alert_level', 'privacy'
        ]

    def to_representation(self, instance):
        return AlertSerializer(instance, context=self.context).data

