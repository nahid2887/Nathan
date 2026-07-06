import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f"chat_{self.conversation_id}"

        # Check if user is participant of the conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send previous messages (history) on connection
        history = await self.get_message_history()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        message_content = data.get('message', '').strip()
        if not message_content:
            return

        # Save message to DB and update conversation timestamp
        message_data = await self.save_message(message_content)

        # Get updated history of messages (including the new one)
        history = await self.get_message_history()

        # Broadcast message and updated history to the chat group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message_data,
                'messages': history
            }
        )

        # Trigger conversation list updates to participants
        await self.trigger_conversation_list_updates()

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'messages': event.get('messages', [])
        }))

    @database_sync_to_async
    def check_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def get_message_history(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            messages = conversation.messages.all().order_by('created_at')
            return MessageSerializer(messages, many=True).data
        except Conversation.DoesNotExist:
            return []

    @database_sync_to_async
    def save_message(self, content):
        conversation = Conversation.objects.get(id=self.conversation_id)
        # Update updated_at of the conversation
        conversation.save() # auto_now updates updated_at
        
        msg = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )
        return MessageSerializer(msg).data

    async def trigger_conversation_list_updates(self):
        participants = await self.get_participants()
        for participant_id in participants:
            await self.channel_layer.group_send(
                f"conversations_{participant_id}",
                {
                    'type': 'conversations_update',
                    'message': 'New message received'
                }
            )

    @database_sync_to_async
    def get_participants(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return list(conversation.participants.values_list('id', flat=True))
        except Conversation.DoesNotExist:
            return []


class ConversationListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"conversations_{self.user.id}"

        # Join personal conversations update group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial conversation list
        await self.send_conversations()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def conversations_update(self, event):
        await self.send_conversations()

    async def send_conversations(self):
        conversations_data = await self.get_conversations()
        await self.send(text_data=json.dumps(conversations_data))

    @database_sync_to_async
    def get_conversations(self):
        # We need to supply request context or just serialize directly passing the user in context
        conversations = Conversation.objects.filter(participants=self.user).order_by('-updated_at')
        serializer = ConversationSerializer(conversations, many=True, context={'user': self.user})
        return serializer.data
