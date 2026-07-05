from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from .models import Recommendation
from .serializers import RecommendationSerializer, RecommendationWriteSerializer, RecommendationCommentSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a recommendation to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow liking, commenting, and sharing for any authenticated user
        if view.action in ['like', 'comment', 'share']:
            return True

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

    @swagger_auto_schema(
        method='post',
        operation_summary="Like/Unlike a Recommendation",
        operation_description="Toggle like on a recommendation for the authenticated user.",
        request_body=no_body,
        responses={200: openapi.Response("Toggled Like status")},
        tags=['Recommendations']
    )
    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        recommendation = self.get_object()
        like_qs = recommendation.likes.filter(user=request.user)
        if like_qs.exists():
            like_qs.delete()
            return Response({'liked': False, 'likes_count': recommendation.likes.count()}, status=status.HTTP_200_OK)
        else:
            recommendation.likes.create(user=request.user)
            return Response({'liked': True, 'likes_count': recommendation.likes.count()}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method='post',
        operation_summary="Add Comment to a Recommendation",
        operation_description="Add a text comment to a recommendation.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['content'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING, description='Comment content')
            }
        ),
        responses={201: RecommendationCommentSerializer()},
        tags=['Recommendations']
    )
    @action(detail=True, methods=['post'], url_path='comment')
    def comment(self, request, pk=None):
        recommendation = self.get_object()
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = recommendation.comments.create(user=request.user, content=content)
        serializer = RecommendationCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method='post',
        operation_summary="Share a Recommendation",
        operation_description="Increment share count/record a share action for a recommendation.",
        request_body=no_body,
        responses={201: openapi.Response("Shared status")},
        tags=['Recommendations']
    )
    @action(detail=True, methods=['post'], url_path='share')
    def share(self, request, pk=None):
        recommendation = self.get_object()
        recommendation.shares.create(user=request.user)
        return Response({'shared': True, 'shares_count': recommendation.shares.count()}, status=status.HTTP_201_CREATED)


