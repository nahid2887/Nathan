import math
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Event
from .serializers import EventSerializer, EventWriteSerializer, UpcomingItemSerializer
from recommendations.models import Recommendation
from recommendations.serializers import RecommendationSerializer
from looking_for.models import LookingFor
from looking_for.serializers import LookingForSerializer


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
        operation_summary="Get Upcoming Events and Recommendations within Distance Radius",
        operation_description="Retrieve upcoming events and recommendations from other users that are within the user's distance_radius (in km) or created by the user's friends.",
        responses={
            200: UpcomingItemSerializer(many=True),
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

        # Fetch friend IDs
        from accounts.models import Friendship
        from django.db.models import Q
        
        friendships = Friendship.objects.filter(
            Q(status='accepted') & (Q(sender=user) | Q(receiver=user))
        )
        friend_ids = set()
        for f in friendships:
            if f.sender == user:
                friend_ids.add(f.receiver_id)
            else:
                friend_ids.add(f.sender_id)

        # Fetch upcoming events created by other users
        events = Event.objects.filter(date_time__gte=now).exclude(creator=user)

        # Fetch recommendations created by other users
        recommendations = Recommendation.objects.exclude(creator=user)

        # Fetch looking_for requests created by other users
        looking_fors = LookingFor.objects.exclude(creator=user)

        combined_items = []

        # Process events
        for event in events:
            is_friend = event.creator_id in friend_ids
            dist = None
            if event.latitude is not None and event.longitude is not None:
                dist = haversine_distance(user.latitude, user.longitude, event.latitude, event.longitude)
            
            if is_friend or (dist is not None and dist <= radius):
                event_data = EventSerializer(event, context={'request': request}).data
                event_data['type'] = 'event'
                event_data['distance_km'] = round(dist, 2) if dist is not None else None
                combined_items.append(event_data)

        # Process recommendations
        for rec in recommendations:
            is_friend = rec.creator_id in friend_ids
            dist = None
            if rec.latitude is not None and rec.longitude is not None:
                dist = haversine_distance(user.latitude, user.longitude, rec.latitude, rec.longitude)

            if is_friend or (dist is not None and dist <= radius):
                rec_data = RecommendationSerializer(rec, context={'request': request}).data
                rec_data['type'] = 'recommendation'
                rec_data['distance_km'] = round(dist, 2) if dist is not None else None
                combined_items.append(rec_data)

        # Process looking_for requests
        for lf in looking_fors:
            is_friend = lf.creator_id in friend_ids
            dist = None
            if lf.latitude is not None and lf.longitude is not None:
                dist = haversine_distance(user.latitude, user.longitude, lf.latitude, lf.longitude)

            if is_friend or (dist is not None and dist <= radius):
                lf_data = LookingForSerializer(lf, context={'request': request}).data
                lf_data['type'] = 'looking_for'
                lf_data['distance_km'] = round(dist, 2) if dist is not None else None
                combined_items.append(lf_data)

        # Process posts from friends
        from posts.models import Post
        from posts.serializers import PostSerializer
        
        friend_posts = Post.objects.filter(creator_id__in=friend_ids)
        for post in friend_posts:
            post_data = PostSerializer(post, context={'request': request}).data
            post_data['type'] = 'post'
            post_data['distance_km'] = None
            combined_items.append(post_data)

        # Sort combined list by distance_km (ascending). Put items with None distance at the end.
        combined_items.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else float('inf'))

        return Response(combined_items, status=status.HTTP_200_OK)
