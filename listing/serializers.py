from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Listing, ListingPhoto

User = get_user_model()

class ListingCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class ListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ['id', 'image']

class ListingSerializer(serializers.ModelSerializer):
    creator = ListingCreatorSerializer(read_only=True)
    photos = ListingPhotoSerializer(many=True, read_only=True)
    type = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'creator', 'title', 'category', 'status', 'price',
            'condition', 'description', 'latitude', 'longitude',
            'location_name', 'pickup_date', 'photos', 'created_at', 'updated_at', 'type', 'distance_km'
        ]
        read_only_fields = [
            'id', 'creator', 'photos', 'created_at', 'updated_at', 'type', 'distance_km'
        ]

    def get_type(self, obj):
        return 'listing'

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

class ListingWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'category', 'status', 'price',
            'condition', 'description', 'latitude', 'longitude',
            'location_name', 'pickup_date', 'photos'
        ]

    def validate_photos(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("You can upload up to 10 photos only.")
        return value

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        
        request = self.context.get('request')
        files = request.FILES.getlist('photos') if request else []
        total_photos = len(files) if files else len(photos_data)
        if total_photos > 10:
            raise serializers.ValidationError({"photos": "You can upload up to 10 photos only."})
            
        listing = Listing.objects.create(**validated_data)
        
        if files:
            for file in files:
                ListingPhoto.objects.create(listing=listing, image=file)
        else:
            for photo in photos_data:
                ListingPhoto.objects.create(listing=listing, image=photo)
                
        return listing

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('photos', None)
        
        request = self.context.get('request')
        files = request.FILES.getlist('photos') if request else []
        total_photos = len(files) if files else (len(photos_data) if photos_data is not None else 0)
        if total_photos > 10:
            raise serializers.ValidationError({"photos": "You can upload up to 10 photos only."})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if photos_data is not None or files:
            # Delete old photos
            instance.photos.all().delete()
            
            if files:
                for file in files:
                    ListingPhoto.objects.create(listing=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    ListingPhoto.objects.create(listing=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return ListingSerializer(instance, context=self.context).data
