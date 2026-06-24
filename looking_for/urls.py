from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LookingForViewSet

router = DefaultRouter()
router.register('looking_for', LookingForViewSet, basename='looking_for')

urlpatterns = [
    path('', include(router.urls)),
]
