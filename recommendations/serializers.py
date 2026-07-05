from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Recommendation, RecommendationPhoto, RecommendationComment, RecommendationLike, RecommendationShare

User = get_user_model()

class RecommendationCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class RecommendationPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationPhoto
        fields = ['id', 'image']

class RecommendationCommentSerializer(serializers.ModelSerializer):
    user = RecommendationCreatorSerializer(read_only=True)

    class Meta:
        model = RecommendationComment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class RecommendationSerializer(serializers.ModelSerializer):
    creator = RecommendationCreatorSerializer(read_only=True)
    photos = RecommendationPhotoSerializer(many=True, read_only=True)
    type = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    has_liked = serializers.SerializerMethodField()
    comments = RecommendationCommentSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    shares_count = serializers.IntegerField(source='shares.count', read_only=True)
    has_shared = serializers.SerializerMethodField()

    class Meta:
        model = Recommendation
        fields = [
            'id', 'creator', 'category', 'rating', 
            'business_name', 'details', 'latitude', 'longitude', 'location_name',
            'photos', 'created_at', 'updated_at', 'type', 'distance_km',
            'likes_count', 'has_liked', 'comments', 'comments_count', 'shares_count', 'has_shared'
        ]
        read_only_fields = [
            'id', 'creator', 'photos', 'created_at', 'updated_at', 'type', 'distance_km',
            'likes_count', 'has_liked', 'comments', 'comments_count', 'shares_count', 'has_shared'
        ]

    def get_type(self, obj):
        return 'recommendation'

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

    def get_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_has_shared(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.shares.filter(user=request.user).exists()
        return False


class RecommendationWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        required=False,
        write_only=True
    )

    class Meta:
        model = Recommendation
        fields = [
            'category', 'rating', 'business_name', 
            'details', 'latitude', 'longitude', 'location_name', 'photos'
        ]

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        recommendation = Recommendation.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                RecommendationPhoto.objects.create(recommendation=recommendation, image=file)
        else:
            for photo in photos_data:
                RecommendationPhoto.objects.create(recommendation=recommendation, image=photo)
                
        return recommendation

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('photos', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        request = self.context.get('request')
        if photos_data is not None or (request and 'photos' in request.FILES):
            # Delete old photos associated with this recommendation
            instance.photos.all().delete()
            
            files = request.FILES.getlist('photos') if request else []
            if files:
                for file in files:
                    RecommendationPhoto.objects.create(recommendation=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    RecommendationPhoto.objects.create(recommendation=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return RecommendationSerializer(instance, context=self.context).data
