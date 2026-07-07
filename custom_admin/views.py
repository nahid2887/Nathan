from rest_framework import viewsets, permissions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer

class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow superusers to create, update, or delete.
    Authenticated users can view/retrieve the list of subscription plans.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing and managing Subscription Plans.
    Only superadmins can create, update, or delete plans.
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsSuperUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="List all Subscription Plans",
        operation_description="Allows authenticated users to list all available subscription plans.",
        responses={200: SubscriptionPlanSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Subscription Plan",
        operation_description="Allows authenticated users to view details of a specific subscription plan by ID.",
        responses={200: SubscriptionPlanSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new Subscription Plan",
        operation_description="Exclusively allows superadmin users to create a new subscription plan.",
        request_body=SubscriptionPlanSerializer,
        responses={201: SubscriptionPlanSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a Subscription Plan",
        operation_description="Exclusively allows superadmin users to modify an existing subscription plan.",
        request_body=SubscriptionPlanSerializer,
        responses={200: SubscriptionPlanSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially update a Subscription Plan",
        operation_description="Exclusively allows superadmin users to partially modify an existing subscription plan.",
        request_body=SubscriptionPlanSerializer,
        responses={200: SubscriptionPlanSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Subscription Plan",
        operation_description="Exclusively allows superadmin users to delete a subscription plan by ID.",
        responses={24: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
