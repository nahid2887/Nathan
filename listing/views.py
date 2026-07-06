from rest_framework import viewsets, permissions, status, parsers
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Listing
from .serializers import ListingSerializer, ListingWriteSerializer

class IsCreatorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.creator == request.user

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Listing.objects.none()
        return Listing.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ListingWriteSerializer
        return ListingSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        request_body=ListingWriteSerializer,
        responses={201: ListingSerializer()},
        tags=['Listings'],
        operation_summary="Create a new classified Listing"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ListingWriteSerializer,
        responses={200: ListingSerializer()},
        tags=['Listings'],
        operation_summary="Update a classified Listing"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ListingWriteSerializer,
        responses={200: ListingSerializer()},
        tags=['Listings'],
        operation_summary="Partially update a classified Listing"
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
