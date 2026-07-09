from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ProductAd, ProductAdPhoto

User = get_user_model()

class ProductAdCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class ProductAdPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAdPhoto
        fields = ['id', 'image']

class ProductAdSerializer(serializers.ModelSerializer):
    creator = ProductAdCreatorSerializer(read_only=True)
    photos = ProductAdPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ProductAd
        fields = [
            'id', 'creator', 'name', 'category', 'description', 
            'phone_number', 'email_address', 'website', 
            'latitude', 'longitude', 'location_name', 
            'business_hours', 'photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'photos', 'created_at', 'updated_at']

class ProductAdWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        model = ProductAd
        fields = [
            'name', 'category', 'description', 'phone_number', 'email_address',
            'website', 'latitude', 'longitude', 'location_name', 'business_hours', 'photos'
        ]

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        product_ad = ProductAd.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                ProductAdPhoto.objects.create(product_ad=product_ad, image=file)
        else:
            for photo in photos_data:
                ProductAdPhoto.objects.create(product_ad=product_ad, image=photo)
                
        return product_ad

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
                    ProductAdPhoto.objects.create(product_ad=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    ProductAdPhoto.objects.create(product_ad=instance, image=photo)
                    
        return instance

    def to_representation(self, instance):
        return ProductAdSerializer(instance, context=self.context).data
