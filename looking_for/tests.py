import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import LookingFor, LookingForPhoto

User = get_user_model()

class LookingForAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('looking_for-list')

        # Create two test users
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            first_name="User One"
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            first_name="User Two"
        )

        # Get JWT tokens for authentication
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)

        # Helper method for mock images
        self.mock_photos = []
        for i in range(2):
            file = io.BytesIO()
            image = Image.new('RGBA', size=(100, 100), color=(100 + i * 20, 100, 100))
            image.save(file, 'png')
            file.name = f'test_image_{i}.png'
            file.seek(0)
            uploaded_file = SimpleUploadedFile(
                f"test_image_{i}.png",
                file.read(),
                content_type="image/png"
            )
            self.mock_photos.append(uploaded_file)

    def test_unauthorized_endpoints(self):
        # 1. List
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create a sample request manually to test details, update, delete
        lf = LookingFor.objects.create(
            creator=self.user1,
            category="Services",
            details="Need a plumber",
            latitude=23.780769,
            longitude=90.407599
        )
        detail_url = reverse('looking_for-detail', args=[lf.id])

        # 2. Retrieve detail
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Create
        response = self.client.post(self.list_create_url, {"details": "Unauthorized Request"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. Update
        response = self.client.patch(detail_url, {"details": "Unauthorized Update"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 5. Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_looking_for_success_json(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "category": "Services (Plumbing)",
            "details": "Need a reliable plumber ASAP.",
            "latitude": "23.7807692141219000",
            "longitude": "90.4075994222697300"
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], "Services (Plumbing)")
        self.assertEqual(response.data['creator']['email'], self.user1.email)
        self.assertEqual(float(response.data['latitude']), 23.7807692141219)
        self.assertEqual(float(response.data['longitude']), 90.40759942226973)
        self.assertEqual(response.data['type'], "looking_for")

    def test_create_looking_for_success_multipart_multiple_photos(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "category": "Food (Cafes)",
            "business_name": "Richmond Espresso",
            "details": "Where can I find the best sourdough toast?",
            "latitude": "23.7800000000000000",
            "longitude": "90.4000000000000000",
            "photos": self.mock_photos  # list of 2 image files
        }
        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], "Food (Cafes)")
        self.assertEqual(len(response.data['photos']), 2)
        
        lf = LookingFor.objects.get(id=response.data['id'])
        self.assertEqual(lf.photos.count(), 2)

    def test_list_and_retrieve_looking_for(self):
        # Set User 1 coordinates
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.save()

        # Create requests under different users
        lf1 = LookingFor.objects.create(
            creator=self.user1,
            category="Cat 1",
            details="Details 1"
        )
        lf2 = LookingFor.objects.create(
            creator=self.user2,
            category="Cat 2",
            details="Details 2",
            latitude=23.790000,
            longitude=90.410000
        )

        # Retrieve list as User 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Retrieve detail of User 2's request as User 1
        detail_url = reverse('looking_for-detail', args=[lf2.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['details'], "Details 2")
        self.assertEqual(response.data['creator']['email'], self.user2.email)
        self.assertEqual(response.data['type'], "looking_for")
        self.assertIsNotNone(response.data['distance_km'])
        self.assertLess(response.data['distance_km'], 2.0)

    def test_update_looking_for_permissions_and_photo_replacement(self):
        # Create a request with initial photo
        lf = LookingFor.objects.create(
            creator=self.user1,
            category="Initial Cat",
            details="Initial Details"
        )
        # Create a photo manually
        LookingForPhoto.objects.create(looking_for=lf, image=self.mock_photos[0])
        self.assertEqual(lf.photos.count(), 1)

        detail_url = reverse('looking_for-detail', args=[lf.id])

        # Try updating as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.patch(detail_url, {"details": "Hacked Details"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        lf.refresh_from_db()
        self.assertEqual(lf.details, "Initial Details")

        # Update details and photos as User 1 (creator) -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # Prepare a new photo list (using the remaining mock photo)
        new_photos = [self.mock_photos[1]]
        data = {
            "details": "Updated Details",
            "photos": new_photos
        }
        
        response = self.client.patch(detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lf.refresh_from_db()
        self.assertEqual(lf.details, "Updated Details")
        # Existing photos should have been replaced with the new photo
        self.assertEqual(lf.photos.count(), 1)
        self.assertTrue(lf.photos.first().image.name.startswith('looking_for_photos/test_image_1'))

    def test_delete_looking_for_permissions(self):
        lf = LookingFor.objects.create(
            creator=self.user1,
            category="Cat",
            details="Details"
        )
        detail_url = reverse('looking_for-detail', args=[lf.id])

        # Try deleting as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(LookingFor.objects.filter(id=lf.id).exists())

        # Delete as User 1 (creator) -> 204 No Content
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LookingFor.objects.filter(id=lf.id).exists())
