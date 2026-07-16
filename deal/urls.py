from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DealPlanViewSet,
    MyDealSubscriptionView,
    DealPlanSubscribeView,
    DealPlanVerifyView,
    DealViewSet
)

router = DefaultRouter()
router.register(r'deal-plans', DealPlanViewSet, basename='deal-plan')
router.register(r'deals', DealViewSet, basename='deal')

urlpatterns = [
    path('deal-plans/my-subscription/', MyDealSubscriptionView.as_view(), name='deal-plans-my-subscription'),
    path('deal-plans/subscribe/', DealPlanSubscribeView.as_view(), name='deal-plans-subscribe'),
    path('deal-plans/verify/', DealPlanVerifyView.as_view(), name='deal-plans-verify'),

    # Non-hyphenated aliases to support both /deal-plans/ and /deal/plans/
    path('deal/plans/my-subscription/', MyDealSubscriptionView.as_view(), name='deal-plans-my-subscription-alias'),
    path('deal/plans/subscribe/', DealPlanSubscribeView.as_view(), name='deal-plans-subscribe-alias'),
    path('deal/plans/verify/', DealPlanVerifyView.as_view(), name='deal-plans-verify-alias'),

    path('', include(router.urls)),
]
