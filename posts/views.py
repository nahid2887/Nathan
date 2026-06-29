from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Post
from .serializers import PostSerializer, PostWriteSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a post to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator of the post
        return obj.creator == request.user

@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=PostWriteSerializer,
    operation_summary="Create a Post",
    operation_description="Create a new post with content and an optional image.",
    tags=['Posts']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    request_body=PostWriteSerializer,
    operation_summary="Update a Post",
    operation_description="Replace an existing post.",
    tags=['Posts']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    request_body=PostWriteSerializer,
    operation_summary="Partially Update a Post",
    operation_description="Update fields on an existing post.",
    tags=['Posts']
))
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PostWriteSerializer
        return PostSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(creator_id=user_id)
        return queryset

    @swagger_auto_schema(
        method='get',
        operation_summary="Get Current User's Posts",
        operation_description="Retrieve a list of posts created by the authenticated user.",
        responses={200: PostSerializer(many=True)},
        tags=['Posts']
    )
    @action(detail=False, methods=['get'], url_path='my-posts')
    def my_posts(self, request):
        posts = Post.objects.filter(creator=request.user).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
