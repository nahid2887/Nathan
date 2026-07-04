from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Post
from .serializers import PostSerializer, PostWriteSerializer, CommentSerializer


class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a post to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow liking and commenting for any authenticated user
        if view.action in ['like', 'comment']:
            return True

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

    @swagger_auto_schema(
        method='post',
        operation_summary="Like/Unlike a Post",
        operation_description="Toggle like on a post for the authenticated user.",
        responses={200: openapi.Response("Toggled Like status")},
        tags=['Posts']
    )
    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        post = self.get_object()
        like_qs = post.likes.filter(user=request.user)
        if like_qs.exists():
            like_qs.delete()
            return Response({'liked': False, 'likes_count': post.likes.count()}, status=status.HTTP_200_OK)
        else:
            post.likes.create(user=request.user)
            return Response({'liked': True, 'likes_count': post.likes.count()}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method='post',
        operation_summary="Add Comment to a Post",
        operation_description="Add a text comment to a post.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['content'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING, description='Comment content')
            }
        ),
        responses={201: CommentSerializer()},
        tags=['Posts']
    )
    @action(detail=True, methods=['post'], url_path='comment')
    def comment(self, request, pk=None):
        post = self.get_object()
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = post.comments.create(user=request.user, content=content)
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

