from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Business, BusinessPhoto, BusinessProfile, BusinessProfilePhoto

User = get_user_model()

class BusinessCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class BusinessPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPhoto
        fields = ['id', 'image']

class BusinessSerializer(serializers.ModelSerializer):
    creator = BusinessCreatorSerializer(read_only=True)
    photos = BusinessPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'creator', 'name', 'category', 'description', 
            'phone_number', 'email_address', 'website', 
            'latitude', 'longitude', 'location_name', 
            'business_hours', 'photos', 'views_count', 'directions_clicks_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'photos', 'created_at', 'updated_at', 'views_count', 'directions_clicks_count']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not (request and request.user and request.user.is_authenticated and request.user == instance.creator):
            data.pop('views_count', None)
            data.pop('directions_clicks_count', None)
        return data

class BusinessWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        model = Business
        fields = [
            'name', 'category', 'description', 'phone_number', 'email_address',
            'website', 'latitude', 'longitude', 'location_name', 'business_hours', 'photos'
        ]

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        business = Business.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                BusinessPhoto.objects.create(business=business, image=file)
        else:
            for photo in photos_data:
                BusinessPhoto.objects.create(business=business, image=photo)
                
        return business

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('photos', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        request = self.context.get('request')
        if photos_data is not None or (request and 'photos' in request.FILES):
            instance.photos.all().delete()
            
            files = request.FILES.getlist('photos') if request else []
            if files:
                for file in files:
                    BusinessPhoto.objects.create(business=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    BusinessPhoto.objects.create(business=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return BusinessSerializer(instance, context=self.context).data


class BusinessProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfilePhoto
        fields = ['id', 'image']


class BusinessProfileSerializer(serializers.ModelSerializer):
    user = BusinessCreatorSerializer(read_only=True)
    photos = BusinessProfilePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = BusinessProfile
        fields = [
            'id', 'user', 'name', 'category', 'about', 
            'phone_number', 'website', 'service_area', 
            'latitude', 'longitude', 'location_name', 
            'business_hours', 'photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'photos', 'created_at', 'updated_at']


class BusinessProfileWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        model = BusinessProfile
        fields = [
            'name', 'category', 'about', 'phone_number', 'website', 
            'service_area', 'latitude', 'longitude', 'location_name', 
            'business_hours', 'photos'
        ]

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        request = self.context.get('request')
        if request:
            validated_data['user'] = request.user
        business_profile = BusinessProfile.objects.create(**validated_data)
        
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                BusinessProfilePhoto.objects.create(business_profile=business_profile, image=file)
        else:
            for photo in photos_data:
                BusinessProfilePhoto.objects.create(business_profile=business_profile, image=photo)
                
        return business_profile

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('photos', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        request = self.context.get('request')
        if photos_data is not None or (request and 'photos' in request.FILES):
            instance.photos.all().delete()
            
            files = request.FILES.getlist('photos') if request else []
            if files:
                for file in files:
                    BusinessProfilePhoto.objects.create(business_profile=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    BusinessProfilePhoto.objects.create(business_profile=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return BusinessProfileSerializer(instance, context=self.context).data

