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
            "title": "Leak Alert",
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
        self.assertEqual(response.data['title'], "Leak Alert")
        self.assertEqual(response.data['alert_type'], "alert")
        self.assertEqual(response.data['type'], "alert")
        self.assertIn('hours_ago', response.data)
        self.assertLessEqual(response.data['hours_ago'], 0.1)

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

    def test_active_alerts_feed(self):
        from django.utils import timezone
        from datetime import timedelta

        active_url = reverse('alert-active')

        # 1. Alert A: Created 1 hour ago (within 24h)
        alert_a = Alert.objects.create(
            creator=self.user1,
            content="Active alert",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            alert_type="alert",
            privacy="anyone"
        )
        Alert.objects.filter(id=alert_a.id).update(created_at=timezone.now() - timedelta(hours=1))

        # 2. Alert B: Created 25 hours ago (outside 24h)
        alert_b = Alert.objects.create(
            creator=self.user1,
            content="Old alert",
            location_name="Richmond",
            latitude=23.780000,
            longitude=90.400000,
            alert_type="missing",
            privacy="anyone"
        )
        Alert.objects.filter(id=alert_b.id).update(created_at=timezone.now() - timedelta(hours=25))

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')

        # 3. Test active feed without type filter -> should return only Alert A
        response = self.client.get(active_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert_ids = [item['id'] for item in response.data]
        self.assertIn(alert_a.id, alert_ids)
        self.assertNotIn(alert_b.id, alert_ids)

        # 4. Test filtering by alert_type=missing -> should return nothing (Alert B is missing but too old)
        response = self.client.get(active_url, {'alert_type': 'missing'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # 5. Test filtering by alert_type=alert -> should return Alert A
        response = self.client.get(active_url, {'alert_type': 'alert'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], alert_a.id)

    def test_create_anonymous_alert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "title": "Anonymous Emergency",
            "content": "Need help anonymously",
            "location_name": "Central Park",
            "latitude": "23.780769",
            "longitude": "90.407599",
            "alert_type": "emergency",
            "alert_level": "critical",
            "is_anonymous": True
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_anonymous'])
        self.assertIsNone(response.data['creator'])

        # Active feed check
        active_url = reverse('alert-active')
        active_res = self.client.get(active_url)
        anon_alert = next(item for item in active_res.data if item['id'] == response.data['id'])
        self.assertIsNone(anon_alert['creator'])

    def test_photo_upload_and_retrieval(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        photo_file = SimpleUploadedFile("alert_photo.gif", small_gif, content_type="image/gif")

        data = {
            "title": "Photo Alert",
            "content": "Alert with image",
            "location_name": "Coogee Beach",
            "latitude": "23.780769",
            "longitude": "90.407599",
            "photo": photo_file
        }
        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['photo'])
        self.assertIn('alert_photo', response.data['photo'])

    def test_toggle_is_anonymous_on_update(self):
        # 1. Create alert with is_anonymous=False
        alert = Alert.objects.create(
            creator=self.user1,
            title="Standard Alert",
            content="Standard content",
            location_name="Bondi",
            latitude=23.780000,
            longitude=90.400000,
            is_anonymous=False
        )
        detail_url = reverse('alert-detail', args=[alert.id])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')

        # Initially creator is visible
        res1 = self.client.get(detail_url)
        self.assertIsNotNone(res1.data['creator'])

        # 2. PATCH is_anonymous = True
        res2 = self.client.patch(detail_url, {"is_anonymous": True})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data['is_anonymous'])
        self.assertIsNone(res2.data['creator'])

        # 3. PATCH is_anonymous = False
        res3 = self.client.patch(detail_url, {"is_anonymous": False})
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertFalse(res3.data['is_anonymous'])
        self.assertIsNotNone(res3.data['creator'])

    def test_create_alert_missing_required_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        # Omit location_name, latitude, and longitude
        data = {
            "title": "Incomplete Alert",
            "content": "Missing location"
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location_name', response.data)
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)

    def test_anonymous_alert_with_friends_privacy(self):
        user3 = User.objects.create_user(
            username="user3_anon@example.com",
            email="user3_anon@example.com",
            password="password123!"
        )
        token3 = str(RefreshToken.for_user(user3).access_token)

        # Friend relationship between user1 and user2
        from accounts.models import Friendship
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status='accepted')

        # Create alert as user1 with privacy='friends' and is_anonymous=True
        anon_friends_alert = Alert.objects.create(
            creator=self.user1,
            title="Friend Anon Alert",
            content="Secret friend alert",
            location_name="Manly",
            latitude=23.780000,
            longitude=90.400000,
            privacy="friends",
            is_anonymous=True
        )

        # Friend (user2) sees the alert in list, but creator is null
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        res_user2 = self.client.get(self.list_create_url)
        self.assertEqual(res_user2.status_code, status.HTTP_200_OK)
        alert_ids = [item['id'] for item in res_user2.data]
        self.assertIn(anon_friends_alert.id, alert_ids)
        item_user2 = next(i for i in res_user2.data if i['id'] == anon_friends_alert.id)
        self.assertIsNone(item_user2['creator'])

        # Non-friend (user3) does NOT see the alert
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token3}')
        res_user3 = self.client.get(self.list_create_url)
        self.assertEqual(res_user3.status_code, status.HTTP_200_OK)
        alert_ids_3 = [item['id'] for item in res_user3.data]
        self.assertNotIn(anon_friends_alert.id, alert_ids_3)


