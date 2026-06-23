from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from .models import Recommendation
from .serializers import RecommendationSerializer, RecommendationWriteSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a recommendation to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator of the recommendation
        return obj.creator == request.user

@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=RecommendationWriteSerializer,
    consumes=['application/json']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    request_body=RecommendationWriteSerializer,
    consumes=['application/json']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    request_body=RecommendationWriteSerializer,
    consumes=['application/json']
))
class RecommendationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Recommendation instances.
    """
    queryset = Recommendation.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecommendationWriteSerializer
        return RecommendationSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
