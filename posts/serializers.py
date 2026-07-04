from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Like, Comment

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

class PostSerializer(serializers.ModelSerializer):
    creator = PostCreatorSerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    has_liked = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'creator', 'content', 'image', 
            'likes_count', 'has_liked', 'comments', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def get_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

class PostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['content', 'image']

    def to_representation(self, instance):
        return PostSerializer(instance, context=self.context).data

