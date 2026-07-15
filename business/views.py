from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Business, BusinessProfile
from .serializers import (
    BusinessSerializer, 
    BusinessWriteSerializer, 
    BusinessProfileSerializer, 
    BusinessProfileWriteSerializer
)
from .permissions import HasActiveSubscription, HasActiveSubscriptionForWrite


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

    def get_queryset(self):
        queryset = Business.objects.all().order_by('-created_at')
        if self.action == 'list' and self.request.user and self.request.user.is_authenticated:
            queryset = queryset.exclude(creator=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BusinessWriteSerializer
        return BusinessSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="List other users' Businesses",
        operation_description="Retrieve a list of businesses created by other users.",
        tags=['Business']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="List own Businesses",
        operation_description="Retrieve a list of businesses created by the currently logged-in user.",
        tags=['Business']
    )
    @action(detail=False, methods=['get'], url_path='my')
    def my_businesses(self, request):
        queryset = Business.objects.filter(creator=request.user).order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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


class BusinessProfileView(APIView):
    """
    API View for managing a user's single business profile.
    Only accessible by active subscribers.
    """
    permission_classes = [permissions.IsAuthenticated, HasActiveSubscription]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Retrieve own Business Profile",
        operation_description="Get the business profile for the currently logged in subscriber.",
        responses={200: BusinessProfileSerializer(), 404: "Not Found"},
        tags=['Business Profile']
    )
    def get(self, request):
        try:
            profile = request.user.business_profile
        except BusinessProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create own Business Profile",
        operation_description="Create a unique business profile for the currently logged in subscriber.",
        request_body=BusinessProfileWriteSerializer,
        responses={201: BusinessProfileSerializer(), 400: "Bad Request"},
        tags=['Business Profile']
    )
    def post(self, request):
        if hasattr(request.user, 'business_profile'):
            return Response(
                {"success": False, "message": "A business profile already exists for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BusinessProfileWriteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            return Response(BusinessProfileSerializer(profile, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Update own Business Profile",
        operation_description="Update the business profile for the currently logged in subscriber.",
        request_body=BusinessProfileWriteSerializer,
        responses={200: BusinessProfileSerializer(), 404: "Not Found", 400: "Bad Request"},
        tags=['Business Profile']
    )
    def put(self, request):
        try:
            profile = request.user.business_profile
        except BusinessProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = BusinessProfileWriteSerializer(profile, data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            return Response(BusinessProfileSerializer(profile, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Partially Update own Business Profile",
        operation_description="Partially update the business profile for the currently logged in subscriber.",
        request_body=BusinessProfileWriteSerializer,
        responses={200: BusinessProfileSerializer(), 404: "Not Found", 400: "Bad Request"},
        tags=['Business Profile']
    )
    def patch(self, request):
        try:
            profile = request.user.business_profile
        except BusinessProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = BusinessProfileWriteSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            return Response(BusinessProfileSerializer(profile, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete own Business Profile",
        operation_description="Delete the business profile for the currently logged in subscriber.",
        responses={204: "No Content", 404: "Not Found"},
        tags=['Business Profile']
    )
    def delete(self, request):
        try:
            profile = request.user.business_profile
        except BusinessProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

