from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Conversation, Message
from .serializers import ConversationSerializer, ConversationCreateSerializer, MessageSerializer

User = get_user_model()

class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user or user.is_anonymous:
            return Conversation.objects.none()
            
        queryset = Conversation.objects.filter(participants=user).order_by('-updated_at')
        
        search_query = self.request.query_params.get('search')
        if search_query:
            # Filter conversations where the OTHER participant's first_name or email matches the search query
            matching_users = User.objects.filter(
                Q(first_name__icontains=search_query) | Q(email__icontains=search_query)
            ).exclude(id=user.id)
            queryset = queryset.filter(participants__in=matching_users)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    @swagger_auto_schema(
        request_body=ConversationCreateSerializer,
        responses={201: ConversationSerializer()},
        tags=['Conversations']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        receiver_id = serializer.validated_data['receiver_id']
        
        if receiver_id == request.user.id:
            return Response(
                {"detail": "You cannot start a conversation with yourself."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Receiver user not found."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check if conversation already exists between these two users
        conversation = Conversation.objects.filter(participants=request.user).filter(participants=receiver).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, receiver)
            
        read_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Mark fetched messages where sender is NOT the current user as read
        unread_messages = instance.messages.filter(is_read=False).exclude(sender=request.user)
        if unread_messages.exists():
            unread_messages.update(is_read=True)
            # Notify conversation list updates to participants
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                for participant in instance.participants.all():
                    async_to_sync(channel_layer.group_send)(
                        f"conversations_{participant.id}",
                        {
                            "type": "conversations_update",
                            "message": "Messages marked as read"
                        }
                    )
                    
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        method='get',
        operation_summary="Get Conversation Messages",
        operation_description="Retrieve paginated messages for a given conversation. Marks retrieved messages from other users as read.",
        responses={200: MessageSerializer(many=True)},
        tags=['Conversations']
    )
    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        conversation = self.get_object()
        
        # Get messages in this conversation
        messages_qs = conversation.messages.all().order_by('created_at')
        
        # Paginate
        paginator = MessagePagination()
        page = paginator.paginate_queryset(messages_qs, request)
        
        # Mark fetched messages where sender is NOT the current user as read
        unread_messages = messages_qs.filter(is_read=False).exclude(sender=request.user)
        if unread_messages.exists():
            unread_messages.update(is_read=True)
            # Notify conversation list updates to participants
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                for participant in conversation.participants.all():
                    # Send websocket update for the conversation list
                    async_to_sync(channel_layer.group_send)(
                        f"conversations_{participant.id}",
                        {
                            "type": "conversations_update",
                            "message": "Messages marked as read"
                        }
                    )
            
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
            
        serializer = MessageSerializer(messages_qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        operation_summary="Mark all messages in a conversation as read",
        responses={200: openapi.Response(description="All messages marked as read")},
        tags=['Conversations']
    )
    @action(detail=True, methods=['post'], url_path='read_all')
    def read_all(self, request, pk=None):
        conversation = self.get_object()
        unread_messages = conversation.messages.filter(is_read=False).exclude(sender=request.user)
        if unread_messages.exists():
            unread_messages.update(is_read=True)
            # Notify participants
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                for participant in conversation.participants.all():
                    async_to_sync(channel_layer.group_send)(
                        f"conversations_{participant.id}",
                        {
                            "type": "conversations_update",
                            "message": "Messages marked as read"
                        }
                    )
        return Response({"detail": "All messages marked as read."}, status=status.HTTP_200_OK)
