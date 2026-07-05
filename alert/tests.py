from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from alert.models import Alert

User = get_user_model()

class AlertAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('alert-list')

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

    def test_list_alerts_authenticated_required(self):
        # 1. Unauthenticated -> 401
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Authenticated -> 200
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_alert_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "content": "Water leak",
            "location_name": "Bondi, NSW",
            "latitude": "23.780769",
            "longitude": "90.407599",
            "alert_type": "alert",
            "alert_level": "high"
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['creator']['email'], self.user1.email)
        self.assertEqual(response.data['alert_type'], "alert")
        self.assertEqual(response.data['type'], "alert")

    def test_update_alert_permissions(self):
        # Create alert as user1
        alert = Alert.objects.create(
            creator=self.user1,
            content="Missing cat",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            alert_type="missing",
            alert_level="medium"
        )
        detail_url = reverse('alert-detail', args=[alert.id])

        # Test updating as non-owner (user2) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.patch(detail_url, {"content": "Hacked content"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test updating as owner (user1) -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.patch(detail_url, {"content": "Found the cat!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert.refresh_from_db()
        self.assertEqual(alert.content, "Found the cat!")

    def test_alert_privacy_filtering(self):
        # Create a third test user
        user3 = User.objects.create_user(
            username="user3@example.com",
            email="user3@example.com",
            password="password123!",
            first_name="User Three"
        )
        token3 = str(RefreshToken.for_user(user3).access_token)

        # Establish Friendship between user1 and user2 (accepted)
        from accounts.models import Friendship
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status='accepted')

        # Create alerts with different privacy settings
        # 1. Alert A: Creator = User 2, Privacy = anyone
        alert_a = Alert.objects.create(
            creator=self.user2,
            content="Anyone alert",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            privacy="anyone"
        )

        # 2. Alert B: Creator = User 2, Privacy = friends
        alert_b = Alert.objects.create(
            creator=self.user2,
            content="Friends-only alert",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            privacy="friends"
        )

        # 3. Alert C: Creator = User 2, Privacy = only_me
        alert_c = Alert.objects.create(
            creator=self.user2,
            content="Private alert",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            privacy="only_me"
        )

        # Test as User 1 (friend of User 2)
        # Should see: Alert A (anyone) and Alert B (friends-only)
        # Should NOT see: Alert C (only_me)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert_ids = [item['id'] for item in response.data]
        self.assertIn(alert_a.id, alert_ids)
        self.assertIn(alert_b.id, alert_ids)
        self.assertNotIn(alert_c.id, alert_ids)

        # Test as User 3 (not a friend of User 2)
        # Should see: Alert A (anyone)
        # Should NOT see: Alert B (friends-only) or Alert C (only_me)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token3}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert_ids = [item['id'] for item in response.data]
        self.assertIn(alert_a.id, alert_ids)
        self.assertNotIn(alert_b.id, alert_ids)
        self.assertNotIn(alert_c.id, alert_ids)

        # Test as User 2 (creator of all alerts)
        # Should see all 3 alerts
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert_ids = [item['id'] for item in response.data]
        self.assertIn(alert_a.id, alert_ids)
        self.assertIn(alert_b.id, alert_ids)
        self.assertIn(alert_c.id, alert_ids)

