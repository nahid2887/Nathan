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

    class Meta:
        model = Event
        fields = [
            'id', 'creator', 'event_banner', 'name', 'date_time', 'location', 
            'latitude', 'longitude', 'description', 'is_ticketed', 
            'require_rsvp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

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

