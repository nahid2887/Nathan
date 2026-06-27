import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Event
from recommendations.models import Recommendation
from looking_for.models import LookingFor

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
        # Set User 1 coordinates
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.save()

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
            location="Loc 2",
            latitude=23.790000,
            longitude=90.410000
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
        self.assertEqual(response.data['type'], "event")
        self.assertIsNotNone(response.data['distance_km'])
        self.assertLess(response.data['distance_km'], 2.0)


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

    def test_upcoming_events_unauthenticated(self):
        upcoming_url = reverse('event-upcoming')
        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upcoming_events_no_user_coordinates(self):
        upcoming_url = reverse('event-upcoming')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # User 1 coordinates are null initially
        self.user1.latitude = None
        self.user1.longitude = None
        self.user1.save()

        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("not set", response.data['message'])

    def test_upcoming_events_distance_filtering(self):
        upcoming_url = reverse('event-upcoming')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')

        # Set User 1 profile: Dhaka city coordinates and a 4 km distance radius
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.distance_radius = 4
        self.user1.save()

        from django.utils import timezone
        from datetime import timedelta

        # Event A: Upcoming, created by User 2, 1.1 km away (INCLUDED)
        event_a = Event.objects.create(
            creator=self.user2,
            name="Event A (Nearby)",
            date_time=timezone.now() + timedelta(days=1),
            location="Nearby Location",
            latitude=23.790000,
            longitude=90.410000
        )

        # Event B: Upcoming, created by User 2, 9 km away (EXCLUDED - too far)
        event_b = Event.objects.create(
            creator=self.user2,
            name="Event B (Far)",
            date_time=timezone.now() + timedelta(days=2),
            location="Far Location",
            latitude=23.850000,
            longitude=90.450000
        )

        # Event C: Past, created by User 2, 1.1 km away (EXCLUDED - not upcoming)
        event_c = Event.objects.create(
            creator=self.user2,
            name="Event C (Past)",
            date_time=timezone.now() - timedelta(days=1),
            location="Nearby Location Past",
            latitude=23.790000,
            longitude=90.410000
        )

        # Event D: Upcoming, created by User 1, 1.1 km away (EXCLUDED - own event)
        event_d = Event.objects.create(
            creator=self.user1,
            name="Event D (Own)",
            date_time=timezone.now() + timedelta(days=1),
            location="Own Location",
            latitude=23.790000,
            longitude=90.410000
        )

        # Recommendation A: Created by User 2, 0.48 km away (INCLUDED - closest)
        rec_a = Recommendation.objects.create(
            creator=self.user2,
            category="Services",
            details="Best plumber near us!",
            latitude=23.785000,
            longitude=90.408000
        )

        # Recommendation B: Created by User 2, 9 km away (EXCLUDED - too far)
        rec_b = Recommendation.objects.create(
            creator=self.user2,
            category="Food",
            details="Great restaurant far away",
            latitude=23.850000,
            longitude=90.450000
        )

        # Recommendation C: Created by User 1, 0.48 km away (EXCLUDED - own recommendation)
        rec_c = Recommendation.objects.create(
            creator=self.user1,
            category="Services",
            details="My own service",
            latitude=23.785000,
            longitude=90.408000
        )

        # LookingFor A: Created by User 2, 0.14 km away (INCLUDED - closest)
        lf_a = LookingFor.objects.create(
            creator=self.user2,
            category="Retail",
            details="Looking for bookstore",
            latitude=23.782000,
            longitude=90.407700
        )

        # LookingFor B: Created by User 2, 9 km away (EXCLUDED - too far)
        lf_b = LookingFor.objects.create(
            creator=self.user2,
            category="Food",
            details="Looking for coffee",
            latitude=23.850000,
            longitude=90.450000
        )

        # LookingFor C: Created by User 1, 0.14 km away (EXCLUDED - own request)
        lf_c = LookingFor.objects.create(
            creator=self.user1,
            category="Retail",
            details="My own bookstore request",
            latitude=23.782000,
            longitude=90.407700
        )

        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify exactly 3 items are returned (LookingFor A, Recommendation A, and Event A)
        self.assertEqual(len(response.data), 3)
        
        # Verify closest item is first: LookingFor A (approx 0.14 km)
        self.assertEqual(response.data[0]['type'], "looking_for")
        self.assertEqual(response.data[0]['details'], "Looking for bookstore")
        self.assertIn('distance_km', response.data[0])
        self.assertLess(response.data[0]['distance_km'], 0.3)
        
        # Verify second closest is Recommendation A (approx 0.48 km)
        self.assertEqual(response.data[1]['type'], "recommendation")
        self.assertEqual(response.data[1]['details'], "Best plumber near us!")
        self.assertIn('distance_km', response.data[1])
        self.assertLess(response.data[1]['distance_km'], 1.0)
        
        # Verify third item is Event A (approx 1.1 km)
        self.assertEqual(response.data[2]['type'], "event")
        self.assertEqual(response.data[2]['name'], "Event A (Nearby)")
        self.assertIn('distance_km', response.data[2])
        self.assertGreater(response.data[2]['distance_km'], 1.0)

        # Verify sorted ascending by distance_km
        self.assertLessEqual(response.data[0]['distance_km'], response.data[1]['distance_km'])
        self.assertLessEqual(response.data[1]['distance_km'], response.data[2]['distance_km'])

    def test_upcoming_events_includes_friends_even_if_far_or_missing_coords(self):
        upcoming_url = reverse('event-upcoming')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')

        # Set User 1 profile: Dhaka city coordinates and a 4 km distance radius
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.distance_radius = 4
        self.user1.save()

        from django.utils import timezone
        from datetime import timedelta
        from accounts.models import Friendship

        # Make User 1 and User 2 friends
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status='accepted')

        # Event A: Upcoming, created by User 2 (Friend), 9 km away (Normally too far, but should be INCLUDED because they are friends)
        event_a = Event.objects.create(
            creator=self.user2,
            name="Friend's Far Event",
            date_time=timezone.now() + timedelta(days=1),
            location="Far Away",
            latitude=23.850000,
            longitude=90.450000
        )

        # Event B: Upcoming, created by User 2 (Friend), has NO coordinates (Normally excluded, but should be INCLUDED because they are friends)
        event_b = Event.objects.create(
            creator=self.user2,
            name="Friend's Coordsless Event",
            date_time=timezone.now() + timedelta(days=2),
            location="Somewhere"
        )

        # Recommendation A: Created by User 2 (Friend), 9 km away (Normally too far, but should be INCLUDED)
        rec_a = Recommendation.objects.create(
            creator=self.user2,
            category="Food",
            details="Friend's restaurant",
            latitude=23.850000,
            longitude=90.450000
        )

        # LookingFor A: Created by User 2 (Friend), 9 km away (Normally too far, but should be INCLUDED)
        lf_a = LookingFor.objects.create(
            creator=self.user2,
            category="Retail",
            details="Friend looking for bookstore",
            latitude=23.850000,
            longitude=90.450000
        )

        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should retrieve all 4 items created by User 2 (Friend)
        self.assertEqual(len(response.data), 4)

        # Verify details
        names = [item.get('name') or item.get('details') for item in response.data]
        self.assertIn("Friend's Far Event", names)
        self.assertIn("Friend's Coordsless Event", names)
        self.assertIn("Friend's restaurant", names)
        self.assertIn("Friend looking for bookstore", names)

        # Coordsless event should have distance_km = None and appear at the end of the list
        self.assertIsNone(response.data[-1]['distance_km'])
        self.assertEqual(response.data[-1]['name'], "Friend's Coordsless Event")


