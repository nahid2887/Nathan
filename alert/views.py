from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from .models import Alert
from .serializers import AlertSerializer, AlertWriteSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of an alert to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator of the alert
        return obj.creator == request.user

@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=AlertWriteSerializer,
    consumes=['application/json'],
    tags=['Alerts']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    request_body=AlertWriteSerializer,
    consumes=['application/json'],
    tags=['Alerts']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    request_body=AlertWriteSerializer,
    consumes=['application/json'],
    tags=['Alerts']
))
class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Alert instances.
    """
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AlertWriteSerializer
        return AlertSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Alert.objects.filter(privacy='anyone').order_by('-created_at')

        from accounts.models import Friendship
        from django.db.models import Q

        # Fetch friends
        friendships = Friendship.objects.filter(
            Q(status='accepted') & (Q(sender=user) | Q(receiver=user))
        )
        friend_ids = [f.receiver_id if f.sender == user else f.sender_id for f in friendships]

        # Filter alerts: creator is user OR privacy is anyone OR (privacy is friends AND creator is friend)
        return Alert.objects.filter(
            Q(creator=user) |
            Q(privacy='anyone') |
            Q(privacy='friends', creator_id__in=friend_ids)
        ).order_by('-created_at').distinct()

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


