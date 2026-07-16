from rest_framework import serializers
from .models import DealPlan

class DealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealPlan
        fields = [
            'id',
            'name',
            'price',
            'billing_cycle',
            'discount_offer',
            'active_deals_limit',
            'badge_text',
            'is_most_popular',
            'features',
            'created_at',
            'updated_at'
        ]


class DealCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        from django.contrib.auth import get_user_model
        model = get_user_model()
        fields = ['id', 'full_name', 'email', 'profile_photo']


class DealPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import DealPhoto
        model = DealPhoto
        fields = ['id', 'image']


class DealSerializer(serializers.ModelSerializer):
    creator = DealCreatorSerializer(read_only=True)
    photos = DealPhotoSerializer(many=True, read_only=True)

    class Meta:
        from .models import Deal
        model = Deal
        fields = [
            'id', 'creator', 'title', 'category', 'deal_type', 'description',
            'business_name', 'business_type', 'address', 'latitude', 'longitude',
            'location_name', 'phone_number', 'website', 'social_links',
            'start_date', 'end_date', 'terms_conditions', 'is_active', 'photos',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'photos', 'created_at', 'updated_at']


class DealWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        required=False,
        write_only=True
    )

    class Meta:
        from .models import Deal
        model = Deal
        fields = [
            'title', 'category', 'deal_type', 'description',
            'business_name', 'business_type', 'address', 'latitude', 'longitude',
            'location_name', 'phone_number', 'website', 'social_links',
            'start_date', 'end_date', 'terms_conditions', 'is_active', 'photos'
        ]

    def validate(self, attrs):
        user = self.context['request'].user
        
        # 1. Check deal subscription
        if not user.check_deal_subscription():
            raise serializers.ValidationError("An active deal subscription is required to post a deal.")
            
        # 2. Check active deals count
        from django.utils import timezone
        today = timezone.now().date()
        
        active_deals = user.created_deals.filter(is_active=True, end_date__gte=today)
        if self.instance:
            active_deals = active_deals.exclude(id=self.instance.id)
            
        active_count = active_deals.count()
        limit = user.current_deal_plan.active_deals_limit if user.current_deal_plan else 0
        
        if limit is not None:
            if active_count >= limit:
                raise serializers.ValidationError(f"Your subscription plan is limited to {limit} active deal(s).")
                
        return attrs

    def create(self, validated_data):
        from .models import DealPhoto, Deal
        photos_data = validated_data.pop('photos', [])
        deal = Deal.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                DealPhoto.objects.create(deal=deal, image=file)
        else:
            for photo in photos_data:
                DealPhoto.objects.create(deal=deal, image=photo)
                
        return deal

    def update(self, instance, validated_data):
        from .models import DealPhoto
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
                    DealPhoto.objects.create(deal=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    DealPhoto.objects.create(deal=instance, image=photo)
                    
        return instance

