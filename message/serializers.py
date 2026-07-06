from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()

class MessageParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo']

class MessageSerializer(serializers.ModelSerializer):
    sender = MessageParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'other_participant', 'last_message', 'unread_count', 'messages', 'created_at', 'updated_at']

    def get_other_participant(self, obj):
        request = self.context.get('request')
        # If request is not in context (e.g. from websocket serialization), we can try to fall back to a user parameter passed in context
        current_user = None
        if request and hasattr(request, 'user'):
            current_user = request.user
        else:
            current_user = self.context.get('user')
            
        if not current_user:
            return None
            
        other = obj.participants.exclude(id=current_user.id).first()
        if other:
            return MessageParticipantSerializer(other, context=self.context).data
        return None

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        current_user = None
        if request and hasattr(request, 'user'):
            current_user = request.user
        else:
            current_user = self.context.get('user')
            
        if not current_user:
            return 0
            
        return obj.messages.filter(is_read=False).exclude(sender=current_user).count()

    def get_messages(self, obj):
        messages = obj.messages.all().order_by('created_at')
        return MessageSerializer(messages, many=True, context=self.context).data


class ConversationCreateSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()

    def validate_receiver_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this receiver_id does not exist.")
        return value
