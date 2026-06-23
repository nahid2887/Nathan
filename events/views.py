import math
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Event
from .serializers import EventSerializer, EventWriteSerializer

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    R = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

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

@method_decorator(name='create', decorator=swagger_auto_schema(
    consumes=['multipart/form-data']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    consumes=['multipart/form-data']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    consumes=['multipart/form-data']
))
class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Event instances.
    """
    queryset = Event.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]
    @property
    def parser_classes(self):
        if not hasattr(self, 'request') or self.request is None or 'swagger' in getattr(self.request, 'path', ''):
            return [MultiPartParser, FormParser]
        return [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventWriteSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="Get Upcoming Events within Distance Radius",
        operation_description="Retrieve upcoming events from other users that are within the user's distance_radius (in km).",
        responses={
            200: EventSerializer(many=True),
            400: "Location coordinates not set"
        }
    )
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        user = request.user
        if user.latitude is None or user.longitude is None:
            return Response(
                {
                    "success": False,
                    "message": "User location coordinates (latitude and longitude) are not set in their profile."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        radius = user.distance_radius if user.distance_radius is not None else 25
        now = timezone.now()

        # Fetch upcoming events created by other users
        events = Event.objects.filter(date_time__gte=now).exclude(creator=user)

        filtered_events = []
        for event in events:
            if event.latitude is not None and event.longitude is not None:
                dist = haversine_distance(user.latitude, user.longitude, event.latitude, event.longitude)
                if dist <= radius:
                    filtered_events.append(event)

        serializer = EventSerializer(filtered_events, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
