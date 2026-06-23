from rest_framework import viewsets, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import Event
from .serializers import EventSerializer, EventWriteSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of an event to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator of the event
        return obj.creator == request.user

class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Event instances.
    """
    queryset = Event.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventWriteSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

