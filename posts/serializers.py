from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post

User = get_user_model()

class PostCreatorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class PostSerializer(serializers.ModelSerializer):
    creator = PostCreatorSerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'creator', 'content', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

class PostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['content', 'image']

    def to_representation(self, instance):
        return PostSerializer(instance, context=self.context).data
