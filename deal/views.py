from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import stripe

from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import DealPlan, Deal, SavedDeal
from .serializers import DealPlanSerializer, DealSerializer, DealWriteSerializer

class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow superusers to create, update, or delete.
    Authenticated users can view/retrieve the list of deal plans.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser


class DealPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing and managing Deal Plans.
    Only superadmins can create, update, or delete plans.
    """
    queryset = DealPlan.objects.all()
    serializer_class = DealPlanSerializer
    permission_classes = [IsSuperUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="List all Deal Plans",
        operation_description="Allows authenticated users to list all available deal plans.",
        responses={200: DealPlanSerializer(many=True)},
        tags=['Deal Payment']
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "count": len(queryset),
            "plans": serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Retrieve a Deal Plan",
        operation_description="Allows authenticated users to view details of a specific deal plan by ID.",
        responses={200: DealPlanSerializer()},
        tags=['Deal Payment']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new Deal Plan",
        operation_description="Exclusively allows superadmin users to create a new deal plan.",
        request_body=DealPlanSerializer,
        responses={201: DealPlanSerializer()},
        tags=['Deal Payment']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a Deal Plan",
        operation_description="Exclusively allows superadmin users to modify an existing deal plan.",
        request_body=DealPlanSerializer,
        responses={200: DealPlanSerializer()},
        tags=['Deal Payment']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update a Deal Plan",
        operation_description="Exclusively allows superadmin users to partially modify an existing deal plan.",
        request_body=DealPlanSerializer,
        responses={200: DealPlanSerializer()},
        tags=['Deal Payment']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Deal Plan",
        operation_description="Exclusively allows superadmin users to remove an existing deal plan.",
        tags=['Deal Payment']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class MyDealSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get own Deal Subscription",
        operation_description="Retrieve details of the active deal subscription for the logged-in user.",
        tags=['Deal Payment'],
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "is_deal_subscribed": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "deal_subscription_expiry": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True),
                        "current_deal_plan": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            nullable=True,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                                "price": openapi.Schema(type=openapi.TYPE_STRING),
                                "billing_cycle": openapi.Schema(type=openapi.TYPE_STRING),
                                "discount_offer": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "active_deals_limit": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "badge_text": openapi.Schema(type=openapi.TYPE_STRING),
                                "is_most_popular": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                "features": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING))
                            }
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        user = request.user
        user.check_deal_subscription()
        
        plan_data = DealPlanSerializer(user.current_deal_plan).data if user.current_deal_plan else None
        
        return Response({
            "is_deal_subscribed": user.is_deal_subscribed,
            "deal_subscription_expiry": user.deal_subscription_expiry,
            "current_deal_plan": plan_data
        }, status=status.HTTP_200_OK)


class DealPlanSubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Stripe Checkout Session for Deal Plan",
        operation_description="Create a Stripe Checkout Session for a specific deal subscription plan.",
        tags=['Deal Payment'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["plan_id"],
            properties={
                "plan_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the deal plan to buy"),
                "success_url": openapi.Schema(type=openapi.TYPE_STRING, description="Optional custom success URL"),
                "cancel_url": openapi.Schema(type=openapi.TYPE_STRING, description="Optional custom cancel URL")
            }
        ),
        responses={
            200: openapi.Response(
                description="Session created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "checkout_url": openapi.Schema(type=openapi.TYPE_STRING),
                        "session_id": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Verification or payload error",
            404: "Plan not found"
        }
    )
    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({"success": False, "message": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = DealPlan.objects.get(id=plan_id)
        except DealPlan.DoesNotExist:
            return Response({"success": False, "message": "Deal plan not found."}, status=status.HTTP_404_NOT_FOUND)

        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')

        if not success_url:
            success_url = request.build_absolute_uri('/api/payment/success/') + '?session_id={CHECKOUT_SESSION_ID}'
        if not cancel_url:
            cancel_url = request.build_absolute_uri('/api/deal-plans/')

        try:
            amount_in_cents = int(plan.price * 100)

            if plan.discount_offer > 0:
                discount_amount = (amount_in_cents * plan.discount_offer) // 100
                amount_in_cents = max(0, amount_in_cents - discount_amount)

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'aud',
                            'product_data': {
                                'name': plan.name,
                                'description': f"Deal Subscription Plan - {plan.get_billing_cycle_display()}",
                            },
                            'unit_amount': amount_in_cents,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': request.user.id,
                    'plan_id': plan.id,
                    'plan_type': 'deal',
                }
            )

            return Response({
                "success": True,
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)





class IsDealCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a deal to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator
        return obj.creator == request.user


class DealViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and managing Deals.
    Create/Update limits are validated based on active subscriptions.
    """
    queryset = Deal.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated, IsDealCreatorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DealWriteSerializer
        return DealSerializer

    def get_queryset(self):
        queryset = Deal.objects.all().order_by('-created_at')
        
        category = self.request.query_params.get('category', '').strip()
        if category:
            queryset = queryset.filter(category__iexact=category)

        search = self.request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(business_name__icontains=search)
            )
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="List all Deals",
        operation_description="Allows authenticated users to list all active deals. Optional query param ?category=<category_name> filters by category, and ?search=<keyword> searches in title, description, or business name.",
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Filter deals by category",
                type=openapi.TYPE_STRING,
                required=False,
                enum=[choice[0] for choice in Deal.CATEGORY_CHOICES]
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search keyword in title, description, or business name",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        tags=['Deals']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Deal",
        operation_description="Retrieve details of a specific deal by ID.",
        tags=['Deals']
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and request.user.is_authenticated and instance.creator != request.user:
            instance.views_count += 1
            instance.save(update_fields=['views_count'])
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new Deal",
        operation_description="Create a new deal listing. Requires an active deal subscription. Limits (e.g. 1 active deal for Starter, 5 for Growth) are automatically enforced.",
        request_body=DealWriteSerializer,
        responses={201: DealSerializer()},
        tags=['Deals']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a Deal",
        operation_description="Modify details of an existing deal. Only allowed by the creator.",
        request_body=DealWriteSerializer,
        responses={200: DealSerializer()},
        tags=['Deals']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update a Deal",
        operation_description="Partially modify details of an existing deal. Only allowed by the creator.",
        request_body=DealWriteSerializer,
        responses={200: DealSerializer()},
        tags=['Deals']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Deal",
        operation_description="Delete an existing deal listing. Only allowed by the creator.",
        tags=['Deals']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        method='get',
        manual_parameters=[
            openapi.Parameter('distance', openapi.IN_QUERY, description="Search radius in kilometers (defaults to user's distance_radius or 25)", type=openapi.TYPE_NUMBER),
            openapi.Parameter('category', openapi.IN_QUERY, description="Filter by category", type=openapi.TYPE_STRING, enum=[choice[0] for choice in Deal.CATEGORY_CHOICES]),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search term in title, description, or business name", type=openapi.TYPE_STRING),
        ],
        responses={200: DealSerializer(many=True)},
        tags=['Deals'],
        operation_summary="Get nearby deals within user's profile distance radius"
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='nearby')
    def nearby(self, request):
        user = request.user
        if user.latitude is None or user.longitude is None:
            return Response(
                {
                    "success": False,
                    "message": "User location coordinates (latitude and longitude) are not set in their profile. Please update your profile with location coordinates first."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        base_lat = float(user.latitude)
        base_lon = float(user.longitude)
        
        dist_param = request.query_params.get('distance')
        if dist_param is not None:
            try:
                radius = float(dist_param)
                if radius < 0:
                    return Response(
                        {
                            "success": False,
                            "message": "Distance cannot be negative."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid distance provided in query parameters. Must be a valid number."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            radius = float(user.distance_radius) if user.distance_radius is not None else 25.0

        deals = Deal.objects.all()
        
        category = request.query_params.get('category', '').strip()
        if category:
            deals = deals.filter(category__iexact=category)

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            deals = deals.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(business_name__icontains=search)
            )

        from events.views import haversine_distance

        nearby_deals = []
        for deal in deals:
            if deal.latitude is not None and deal.longitude is not None:
                dist = haversine_distance(base_lat, base_lon, float(deal.latitude), float(deal.longitude))
                deal.distance_km = round(dist, 2)
            else:
                deal.distance_km = None
            nearby_deals.append(deal)

        # Sort: items with distance first (sorted ascending), then items without distance last
        nearby_deals.sort(key=lambda x: (x.distance_km is None, x.distance_km or 0))

        serializer = DealSerializer(nearby_deals, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: openapi.Response(
            description="Returns phone number and records a call click tap.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Business phone number")
                }
            )
        )},
        tags=['Deals'],
        operation_summary="Record phone call click and get phone number"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='click-call')
    def click_call(self, request, pk=None):
        deal = self.get_object()
        if deal.creator != request.user:
            deal.call_clicks_count += 1
            deal.save(update_fields=['call_clicks_count'])
        return Response({"phone_number": deal.phone_number}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: openapi.Response(
            description="Returns address and coordinates and records a directions click.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "address": openapi.Schema(type=openapi.TYPE_STRING),
                    "location_name": openapi.Schema(type=openapi.TYPE_STRING),
                    "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "longitude": openapi.Schema(type=openapi.TYPE_NUMBER)
                }
            )
        )},
        tags=['Deals'],
        operation_summary="Record directions click and get location info"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='click-directions')
    def click_directions(self, request, pk=None):
        deal = self.get_object()
        if deal.creator != request.user:
            deal.directions_clicks_count += 1
            deal.save(update_fields=['directions_clicks_count'])
        return Response({
            "address": deal.address,
            "location_name": deal.location_name,
            "latitude": deal.latitude,
            "longitude": deal.longitude
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: openapi.Response(
            description="Saves a deal for the authenticated user."
        )},
        tags=['Deals'],
        operation_summary="Save (bookmark) a deal"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='save')
    def save_deal(self, request, pk=None):
        deal = self.get_object()
        if deal.creator == request.user:
            return Response({"success": False, "message": "You cannot save your own deal."}, status=status.HTTP_400_BAD_REQUEST)
        
        saved_deal, created = SavedDeal.objects.get_or_create(user=request.user, deal=deal)
        if created:
            deal.saves_count += 1
            deal.save(update_fields=['saves_count'])
            return Response({"success": True, "message": "Deal saved successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"success": True, "message": "Deal was already saved."}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: openapi.Response(
            description="Unsaves a deal for the authenticated user."
        )},
        tags=['Deals'],
        operation_summary="Unsave (remove bookmark from) a deal"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='unsave')
    def unsave_deal(self, request, pk=None):
        deal = self.get_object()
        try:
            saved_deal = SavedDeal.objects.get(user=request.user, deal=deal)
            saved_deal.delete()
            
            # Decrement saves_count clamped at 0
            if deal.saves_count > 0:
                deal.saves_count -= 1
                deal.save(update_fields=['saves_count'])
                
            return Response({"success": True, "message": "Deal unsaved successfully."}, status=status.HTTP_200_OK)
        except SavedDeal.DoesNotExist:
            return Response({"success": True, "message": "Deal was not saved."}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        responses={200: DealSerializer(many=True)},
        tags=['Deals'],
        operation_summary="List all saved deals of the user"
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='saved')
    def saved(self, request):
        saved_deals = Deal.objects.filter(saved_by_users__user=request.user)
        serializer = DealSerializer(saved_deals, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: DealSerializer()},
        tags=['Deals'],
        operation_summary="Record deal view and get deal details"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='click-view')
    def click_view(self, request, pk=None):
        deal = self.get_object()
        if deal.creator != request.user:
            deal.views_count += 1
            deal.save(update_fields=['views_count'])
        serializer = DealSerializer(deal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        responses={200: openapi.Response(
            description="Returns aggregate engagement analytics and performance for all deals created by the user.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "total_views": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "total_phone_call_taps": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "total_directions_clicks": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "total_saved_deals": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "deals_performance": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )},
        tags=['Deals'],
        operation_summary="Get business/deal analytics for creator"
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='analytics')
    def analytics(self, request):
        user = request.user
        my_deals = Deal.objects.filter(creator=user).order_by('-created_at')

        from django.db.models import Sum
        aggregates = my_deals.aggregate(
            total_views=Sum('views_count'),
            total_phone=Sum('call_clicks_count'),
            total_directions=Sum('directions_clicks_count'),
            total_saves=Sum('saves_count')
        )

        serializer = DealSerializer(my_deals, many=True, context={'request': request})

        data = {
            "total_views": aggregates['total_views'] or 0,
            "total_phone_call_taps": aggregates['total_phone'] or 0,
            "total_directions_clicks": aggregates['total_directions'] or 0,
            "total_saved_deals": aggregates['total_saves'] or 0,
            "deals_performance": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        responses={200: DealSerializer()},
        tags=['Deals'],
        operation_summary="Deactivate a deal created by the user"
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='deactivate')
    def deactivate(self, request, pk=None):
        deal = self.get_object()
        if deal.creator != request.user:
            return Response(
                {"success": False, "message": "You do not have permission to deactivate this deal."},
                status=status.HTTP_403_FORBIDDEN
            )
        deal.is_active = False
        deal.save(update_fields=['is_active'])
        serializer = DealSerializer(deal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

