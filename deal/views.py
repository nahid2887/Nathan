from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import stripe

from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import DealPlan, Deal
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
            success_url = request.build_absolute_uri('/api/deal-plans/verify/') + '?session_id={CHECKOUT_SESSION_ID}'
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


class DealPlanVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Stripe Checkout Session for Deal Plan",
        operation_description="Verify checkout session payment and activate deal subscription.",
        tags=['Deal Payment'],
        manual_parameters=[
            openapi.Parameter('session_id', openapi.IN_QUERY, description="Stripe Session ID", type=openapi.TYPE_STRING, required=True)
        ],
        responses={
            200: openapi.Response(
                description="Deal subscription verified",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_deal_subscribed": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "deal_subscription_expiry": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Verification failed"
        }
    )
    def get(self, request):
        from accounts.models import User

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"success": False, "message": "session_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        if session_id == '{CHECKOUT_SESSION_ID}' or '{CHECKOUT_SESSION_ID}' in session_id:
            return Response({
                "success": False,
                "message": "This is a placeholder checkout session ID template. To verify a payment, please go through the checkout URL returned from the subscribe endpoint, complete the payment, and let Stripe redirect you."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status != 'paid':
                return Response({"success": False, "message": "Session has not been paid yet."}, status=status.HTTP_400_BAD_REQUEST)

            metadata = session.metadata
            user_id = metadata.get('user_id')
            plan_id = metadata.get('plan_id')
            plan_type = metadata.get('plan_type')

            if plan_type != 'deal' or not user_id or not plan_id:
                return Response({"success": False, "message": "Invalid session metadata for deal plans."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(id=user_id)
                plan = DealPlan.objects.get(id=plan_id)
            except (User.DoesNotExist, DealPlan.DoesNotExist):
                return Response({"success": False, "message": "User or Deal Plan from metadata not found."}, status=status.HTTP_400_BAD_REQUEST)

            if plan.billing_cycle == 'monthly':
                duration = timedelta(days=30)
            elif plan.billing_cycle == 'yearly':
                duration = timedelta(days=365)
            else:
                duration = timedelta(days=30)

            now = timezone.now()
            if user.deal_subscription_expiry and user.deal_subscription_expiry > now:
                start_date = user.deal_subscription_expiry
            else:
                start_date = now

            new_expiry = start_date + duration

            user.is_deal_subscribed = True
            user.deal_subscription_expiry = new_expiry
            user.current_deal_plan = plan
            user.save()

            print("\n" + "=" * 60)
            print("STRIPE DEAL PLAN PAYMENT VERIFICATION SUCCESSFUL")
            print(f"Session ID:         {session_id}")
            print(f"User:               {user.username} (ID: {user.id}, Email: {user.email})")
            print(f"Deal Plan:          {plan.name} (ID: {plan.id})")
            print(f"Amount Paid:        AU$ {plan.price}")
            print(f"Billing Cycle:      {plan.get_billing_cycle_display()}")
            print(f"New Expiry Date:    {new_expiry}")
            print("=" * 60 + "\n")

            return Response({
                "success": True,
                "message": "Deal subscription verified and activated successfully.",
                "is_deal_subscribed": user.is_deal_subscribed,
                "deal_subscription_expiry": user.deal_subscription_expiry
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
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @swagger_auto_schema(
        operation_summary="List all Deals",
        operation_description="Allows authenticated users to list all active deals. Optional query param ?category=<category_name> filters by category.",
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Filter deals by category",
                type=openapi.TYPE_STRING,
                required=False,
                enum=[choice[0] for choice in Deal.CATEGORY_CHOICES]
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

