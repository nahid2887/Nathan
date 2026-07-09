from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Listing, ListingPhoto

User = get_user_model()

class ListingAPITests(APITestCase):

    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            latitude="23.780769",
            longitude="90.407599"
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            latitude="23.810332",
            longitude="90.412518"
        )

        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)

        self.list_create_url = reverse('listing-list')

        # Create mock image helper
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )

    def test_create_listing_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # 3 mock photos
        photo1 = SimpleUploadedFile("photo1.gif", self.small_gif, content_type="image/gif")
        photo2 = SimpleUploadedFile("photo2.gif", self.small_gif, content_type="image/gif")
        photo3 = SimpleUploadedFile("photo3.gif", self.small_gif, content_type="image/gif")

        data = {
            "title": "Bicycle",
            "category": "Sports",
            "status": "for_sale",
            "price": "120.00",
            "condition": "like_new",
            "description": "Hardly used bicycle in great condition.",
            "latitude": "23.780700",
            "longitude": "90.407500",
            "location_name": "Gulshan, Dhaka",
            "photos": [photo1, photo2, photo3]
        }

        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], "Bicycle")
        self.assertEqual(response.data['status'], "for_sale")
        self.assertEqual(float(response.data['price']), 120.00)
        self.assertEqual(response.data['condition'], "like_new")
        self.assertEqual(len(response.data['photos']), 3)
        self.assertEqual(response.data['type'], "listing")

    def test_create_listing_photo_limit_error(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # 11 mock photos
        photos = []
        for i in range(11):
            photos.append(SimpleUploadedFile(f"photo{i}.gif", self.small_gif, content_type="image/gif"))

        data = {
            "title": "Bicycle",
            "category": "Sports",
            "status": "for_sale",
            "price": "120.00",
            "condition": "like_new",
            "description": "Hardly used bicycle in great condition.",
            "latitude": "23.780700",
            "longitude": "90.407500",
            "location_name": "Gulshan, Dhaka",
            "photos": photos
        }

        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("photos", response.data)

    def test_list_and_retrieve_listing(self):
        # Create listing
        listing = Listing.objects.create(
            creator=self.user1,
            title="Sofa",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            description="Used sofa, free to pickup.",
            latitude="23.780769",
            longitude="90.407599",
            location_name="Gulshan, Dhaka"
        )
        
        # Public listing retrieval (unauthenticated) -> should now be HTTP_401_UNAUTHORIZED
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Authenticated listing retrieval
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Sofa")
        
        # Authenticated retrieve checking distance
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        detail_url = reverse('listing-detail', args=[listing.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['distance_km'])

    def test_update_delete_permissions(self):
        # Create listing as user1
        listing = Listing.objects.create(
            creator=self.user1,
            title="Table",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.780769",
            longitude="90.407599",
            location_name="Gulshan, Dhaka"
        )

        detail_url = reverse('listing-detail', args=[listing.id])

        # User2 tries to update -> Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        data = {"title": "New Table"}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User1 updates -> Success
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "New Table")

        # User2 tries to delete -> Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User1 deletes -> Success
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_nearby_listings_filtering_by_distance(self):
        # User 1 is at latitude="23.780769", longitude="90.407599" (Gulshan)
        # Set user1's distance_radius to 5 km
        self.user1.distance_radius = 5
        self.user1.save()

        # User 2 is at latitude="23.810332", longitude="90.412518"
        # Create listing 1 (close to user 1, within 5km)
        listing_close = Listing.objects.create(
            creator=self.user2,
            title="Close Item",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.781000",
            longitude="90.408000",
            location_name="Gulshan 1"
        )

        # Create listing 2 (far from user 1, more than 15km)
        listing_far = Listing.objects.create(
            creator=self.user2,
            title="Far Item",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.950000",
            longitude="90.550000",
            location_name="Savar"
        )

        # Create listing 3 (owned by User 1 - should be excluded)
        listing_own = Listing.objects.create(
            creator=self.user1,
            title="My Own Item",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.780769",
            longitude="90.407599",
            location_name="My House"
        )

        nearby_url = reverse('listing-nearby')
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(nearby_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify close item is returned, far and own items are excluded
        titles = [item['title'] for item in response.data]
        self.assertIn("Close Item", titles)
        self.assertNotIn("Far Item", titles)
        self.assertNotIn("My Own Item", titles)

        # Verify distance calculation is returned
        self.assertIsNotNone(response.data[0]['distance_km'])

        # Test filtering by category
        response = self.client.get(nearby_url, {'category': 'Furniture'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Close Item")

        # Create another close listing with category "Books" and status "for_sale"
        Listing.objects.create(
            creator=self.user2,
            title="Book Item",
            category="Books",
            status="for_sale",
            price="10.00",
            condition="new",
            latitude="23.781000",
            longitude="90.408000",
            location_name="Gulshan 1"
        )

        # Test filtering by status "for_sale"
        response = self.client.get(nearby_url, {'status': 'for_sale'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Book Item")

        # Test filtering by status "free"
        response = self.client.get(nearby_url, {'status': 'free'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Close Item")

    def test_authenticated_user_lists_own_listings_only(self):
        # Create listing owned by user 1
        listing_u1 = Listing.objects.create(
            creator=self.user1,
            title="User 1 Item",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.780769",
            longitude="90.407599",
            location_name="Gulshan"
        )
        
        # Create listing owned by user 2
        listing_u2 = Listing.objects.create(
            creator=self.user2,
            title="User 2 Item",
            category="Furniture",
            status="free",
            price="0.00",
            condition="good",
            latitude="23.780769",
            longitude="90.407599",
            location_name="Gulshan"
        )

        # GET request unauthenticated -> should now be HTTP_401_UNAUTHORIZED
        self.client.credentials()
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # GET request logged in as user 1 -> returns only user 1's items
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "User 1 Item")

        # GET request logged in as user 2 -> returns only user 2's items
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "User 2 Item")

