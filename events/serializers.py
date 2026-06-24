from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Event

User = get_user_model()

class EventCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class EventSerializer(serializers.ModelSerializer):
    creator = EventCreatorSerializer(read_only=True)
    event_banner = serializers.ImageField(required=False, allow_null=True)
    type = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'creator', 'event_banner', 'name', 'date_time', 'location', 
            'latitude', 'longitude', 'description', 'is_ticketed', 
            'require_rsvp', 'created_at', 'updated_at', 'type', 'distance_km'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at', 'type', 'distance_km']

    def get_type(self, obj):
        return 'event'

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

class EventWriteSerializer(serializers.ModelSerializer):
    event_banner = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Event
        fields = [
            'event_banner', 'name', 'date_time', 'location', 
            'latitude', 'longitude', 'description', 'is_ticketed', 
            'require_rsvp'
        ]

    def to_representation(self, instance):
        return EventSerializer(instance, context=self.context).data


class UpcomingItemSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="Type of the item: 'event', 'recommendation', or 'looking_for'")
    distance_km = serializers.FloatField(help_text="Distance in kilometers from the user location")
    
    # Common/Event/Recommendation fields
    id = serializers.IntegerField(required=False)
    creator = serializers.DictField(required=False)
    latitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False)
    longitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)

    # Event specific fields
    event_banner = serializers.ImageField(required=False, allow_null=True)
    name = serializers.CharField(required=False)
    date_time = serializers.DateTimeField(required=False)
    location = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_null=True)
    is_ticketed = serializers.BooleanField(required=False)
    require_rsvp = serializers.BooleanField(required=False)

    # Recommendation specific fields
    category = serializers.CharField(required=False)
    rating = serializers.IntegerField(required=False, allow_null=True)
    business_name = serializers.CharField(required=False, allow_null=True)
    details = serializers.CharField(required=False)
    photos = serializers.ListField(required=False)

