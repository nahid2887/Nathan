from django.contrib import admin
from django.urls import path, include

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny


schema_view = get_schema_view(
    openapi.Info(
        title="My API",
        default_version='v1',
        description="API Documentation",
    ),
    public=True,
    permission_classes=[AllowAny],
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include('accounts.urls')),
    path('api/', include('events.urls')),
    path('api/', include('recommendations.urls')),
    path('api/', include('looking_for.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/posts/', include('posts.urls')),


    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)