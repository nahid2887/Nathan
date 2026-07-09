from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import ProductAd
from .serializers import ProductAdSerializer, ProductAdWriteSerializer
from .permissions import HasActiveSubscription, IsCreatorOrReadOnly

@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=ProductAdWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Product Ads']
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    request_body=ProductAdWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Product Ads']
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    request_body=ProductAdWriteSerializer,
    consumes=['multipart/form-data', 'application/json'],
    tags=['Product Ads']
))
class ProductAdViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Product Ads.
    Only accessible by users with active subscriptions.
    """
    queryset = ProductAd.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, HasActiveSubscription, IsCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductAdWriteSerializer
        return ProductAdSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="List all Product Ads",
        operation_description="Retrieve a list of all active product ads. Only accessible to active subscribers.",
        tags=['Product Ads']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Product Ad",
        operation_description="Retrieve details of a specific product ad by ID. Only accessible to active subscribers.",
        tags=['Product Ads']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Product Ad",
        operation_description="Delete a product ad listing. Only accessible by the creator with an active subscription.",
        tags=['Product Ads']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
