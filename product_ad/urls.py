from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductAdViewSet

router = DefaultRouter()
router.register(r'product-ads', ProductAdViewSet, basename='productad')

urlpatterns = [
    path('', include(router.urls)),
]
