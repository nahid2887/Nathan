from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Like, Comment, PostPhoto

User = get_user_model()

class PostCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class CommentSerializer(serializers.ModelSerializer):
    user = PostCreatorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class PostPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostPhoto
        fields = ['id', 'image']

class PostSerializer(serializers.ModelSerializer):
    creator = PostCreatorSerializer(read_only=True)
    photos = PostPhotoSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    has_liked = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'creator', 'title', 'content', 'image', 'photos', 'is_anonymous',
            'location_name', 'latitude', 'longitude',
            'likes_count', 'has_liked', 'comments', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at', 'photos']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data['creator'] = None
        return data

    def get_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

class PostWriteSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'is_anonymous', 'location_name', 'latitude', 'longitude', 'photos']

    def create(self, validated_data):
        photos_data = validated_data.pop('photos', [])
        post = Post.objects.create(**validated_data)
        
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('photos')
            for file in files:
                PostPhoto.objects.create(post=post, image=file)
        else:
            for photo in photos_data:
                PostPhoto.objects.create(post=post, image=photo)
        return post

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
                    PostPhoto.objects.create(post=instance, image=file)
            elif photos_data:
                for photo in photos_data:
                    PostPhoto.objects.create(post=instance, image=photo)
        return instance

    def to_representation(self, instance):
        return PostSerializer(instance, context=self.context).data

