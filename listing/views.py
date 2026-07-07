from rest_framework import viewsets, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.decorators import action
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

    @swagger_auto_schema(
        method='get',
        responses={200: ListingSerializer(many=True)},
        tags=['Listings'],
        operation_summary="Get nearby listings within user's profile distance radius"
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
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid distance provided in query parameters."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            radius = float(user.distance_radius) if user.distance_radius is not None else 25.0

        listings = Listing.objects.exclude(creator=user).filter(latitude__isnull=False, longitude__isnull=False)
        
        category = request.query_params.get('category')
        if category:
            listings = listings.filter(category__icontains=category)

        search = request.query_params.get('search')
        if search:
            listings = listings.filter(title__icontains=search)

        from events.views import haversine_distance

        nearby_listings = []
        for listing in listings:
            dist = haversine_distance(base_lat, base_lon, float(listing.latitude), float(listing.longitude))
            if dist <= radius:
                listing.distance_km = round(dist, 2)
                nearby_listings.append(listing)

        nearby_listings.sort(key=lambda x: x.distance_km)

        serializer = ListingSerializer(nearby_listings, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

