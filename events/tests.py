import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Event

User = get_user_model()

class EventAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('event-list')

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

        # Helper method for a mock image
        file = io.BytesIO()
        image = Image.new('RGBA', size=(100, 100), color=(0, 120, 200))
        image.save(file, 'png')
        file.name = 'test_banner.png'
        file.seek(0)
        self.mock_banner = SimpleUploadedFile(
            "test_banner.png",
            file.read(),
            content_type="image/png"
        )

    def test_unauthorized_endpoints(self):
        # 1. List events
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create a sample event manually to test details, update, delete
        event = Event.objects.create(
            creator=self.user1,
            name="Sample Event",
            date_time="2026-12-31T20:00:00Z",
            location="Sample Location",
            latitude=23.7807692141219,
            longitude=90.40759942226973
        )
        detail_url = reverse('event-detail', args=[event.id])

        # 2. Retrieve event detail
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Create event
        response = self.client.post(self.list_create_url, {"name": "Unauthorized Event"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. Update event
        response = self.client.patch(detail_url, {"name": "Unauthorized Update"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 5. Delete event
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_event_success_json(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "name": "Tech Conference",
            "date_time": "2026-08-15T09:00:00Z",
            "location": "Convention Center, Dhaka",
            "latitude": "23.7807692141219000",
            "longitude": "90.4075994222697300",
            "description": "Annual tech meetup and exhibition.",
            "is_ticketed": True,
            "require_rsvp": True
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Tech Conference")
        self.assertEqual(response.data['creator']['email'], self.user1.email)
        self.assertEqual(float(response.data['latitude']), 23.7807692141219)
        self.assertEqual(float(response.data['longitude']), 90.40759942226973)
        self.assertTrue(response.data['is_ticketed'])
        self.assertTrue(response.data['require_rsvp'])

    def test_create_event_success_multipart(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "name": "Summer Concert",
            "date_time": "2026-07-20T18:00:00Z",
            "location": "Neighborhood Park",
            "latitude": "23.7800000000000000",
            "longitude": "90.4000000000000000",
            "description": "Live music event in the park.",
            "is_ticketed": False,
            "require_rsvp": False,
            "event_banner": self.mock_banner
        }
        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Summer Concert")
        self.assertIsNotNone(response.data['event_banner'])
        
        event = Event.objects.get(id=response.data['id'])
        self.assertTrue(event.event_banner.name.startswith('event_banners/test_banner'))

    def test_list_and_retrieve_events(self):
        # Create events under different users
        event1 = Event.objects.create(
            creator=self.user1,
            name="User 1 Event",
            date_time="2026-08-01T10:00:00Z",
            location="Loc 1"
        )
        event2 = Event.objects.create(
            creator=self.user2,
            name="User 2 Event",
            date_time="2026-08-02T10:00:00Z",
            location="Loc 2"
        )

        # Retrieve list as User 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return both events
        self.assertEqual(len(response.data), 2)

        # Retrieve detail of User 2's event as User 1
        detail_url = reverse('event-detail', args=[event2.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "User 2 Event")
        self.assertEqual(response.data['creator']['email'], self.user2.email)

    def test_update_event_permissions(self):
        event = Event.objects.create(
            creator=self.user1,
            name="Original Event",
            date_time="2026-09-01T10:00:00Z",
            location="Original Loc"
        )
        detail_url = reverse('event-detail', args=[event.id])

        # Try updating as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.patch(detail_url, {"name": "Hacked Event"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        event.refresh_from_db()
        self.assertEqual(event.name, "Original Event")

        # Update as User 1 (creator) -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.patch(detail_url, {"name": "Updated Event"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.name, "Updated Event")

        # Test PUT option (full replace) as creator
        response = self.client.put(detail_url, {
            "name": "Replaced Event",
            "date_time": "2026-09-02T10:00:00Z",
            "location": "New Loc"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.name, "Replaced Event")

    def test_delete_event_permissions(self):
        event = Event.objects.create(
            creator=self.user1,
            name="To Be Deleted Event",
            date_time="2026-10-01T10:00:00Z",
            location="Loc"
        )
        detail_url = reverse('event-detail', args=[event.id])

        # Try deleting as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Event.objects.filter(id=event.id).exists())

        # Delete as User 1 (creator) -> 204 No Content
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(id=event.id).exists())
