from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import LookingFor, LookingForPhoto

User = get_user_model()

class LookingForCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class LookingForPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LookingForPhoto
        fields = ['id', 'image']

class LookingForSerializer(serializers.ModelSerializer):
    creator = LookingForCreatorSerializer(read_only=True)
    photos = LookingForPhotoSerializer(many=True, read_only=True)
    type = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = LookingFor
        fields = [
            'id', 'creator', 'category', 'business_name', 
            'details', 'latitude', 'longitude', 'photos', 
            'created_at', 'updated_at', 'type', 'distance_km'
        ]
        read_only_fields = ['id', 'creator', 'photos', 'created_at', 'updated_at', 'type', 'distance_km']

    def get_type(self, obj):
        return 'looking_for'

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

class LookingForWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        required=False,
        write_only=True
    )

    class Meta:
        model = LookingFor
        fields = [
            'category', 'business_name', 'details', 
            'latitude', 'longitude', 'photos'
        ]

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        looking_for = LookingFor.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                LookingForPhoto.objects.create(looking_for=looking_for, image=file)
        else:
            for photo in photos_data:
                LookingForPhoto.objects.create(looking_for=looking_for, image=photo)
                
        return looking_for

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('photos', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        request = self.context.get('request')
        if photos_data is not None or (request and 'photos' in request.FILES):
            # Delete old photos associated with this model
            instance.photos.all().delete()
            
            files = request.FILES.getlist('photos') if request else []
            if files:
                for file in files:
                    LookingForPhoto.objects.create(looking_for=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    LookingForPhoto.objects.create(looking_for=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return LookingForSerializer(instance, context=self.context).data
