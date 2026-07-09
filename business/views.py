from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Business
from .serializers import BusinessSerializer, BusinessWriteSerializer, BusinessRatingSerializer
from .permissions import HasActiveSubscription

class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a business to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator
        return obj.creator == request.user


@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=BusinessWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Business']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    request_body=BusinessWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Business']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    request_body=BusinessWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Business']
))
class BusinessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Business listings.
    Only accessible by users with active subscriptions.
    """
    queryset = Business.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, HasActiveSubscription, IsCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BusinessWriteSerializer
        return BusinessSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="List all Businesses",
        operation_description="Retrieve a list of all active businesses. Only accessible to active subscribers.",
        tags=['Business']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Business",
        operation_description="Retrieve details of a specific business by ID. Only accessible to active subscribers.",
        tags=['Business']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Business",
        operation_description="Delete a business listing. Only accessible by the creator with an active subscription.",
        tags=['Business']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        method='post',
        operation_summary="Rate a Business",
        operation_description="Submit a rating (1-5) and an optional review for a business. The business owner/creator cannot rate their own business.",
        request_body=BusinessRatingSerializer,
        responses={201: BusinessRatingSerializer(), 400: "Bad Request"},
        tags=['Business']
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, HasActiveSubscription])
    def rate(self, request, pk=None):
        business = self.get_object()
        
        # Prevent the business owner/creator from rating their own business
        if business.creator == request.user:
            return Response(
                {"detail": "You cannot rate or review your own business listing."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = BusinessRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from .models import BusinessRating
        rating_obj, created = BusinessRating.objects.update_or_create(
            business=business,
            user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'review': serializer.validated_data.get('review', '')
            }
        )
        
        response_serializer = BusinessRatingSerializer(rating_obj)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=status_code)
