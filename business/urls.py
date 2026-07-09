from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BusinessViewSet, BusinessProfileView

router = DefaultRouter()
router.register(r'businesses', BusinessViewSet, basename='business')

urlpatterns = [
    path('business-profile/', BusinessProfileView.as_view(), name='business-profile'),
    path('', include(router.urls)),
]
