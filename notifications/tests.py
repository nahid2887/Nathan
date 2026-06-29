from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone

from events.models import Event
from recommendations.models import Recommendation
from looking_for.models import LookingFor
from notifications.models import Notification

User = get_user_model()

class NotificationTests(APITestCase):

    def setUp(self):
        # Create recipient user
        self.recipient = User.objects.create_user(
            username="recipient@example.com",
            email="recipient@example.com",
            password="password123!",
            first_name="Recipient User",
            latitude=23.8103,
            longitude=90.4125,
            distance_radius=25
        )
        # Create creator user
        self.creator = User.objects.create_user(
            username="creator@example.com",
            email="creator@example.com",
            password="password123!",
            first_name="Creator User"
        )
        
        self.login_url = reverse('login')
        self.notifications_url = reverse('notification-list')
        self.unread_count_url = reverse('notification-unread-count')
        self.read_all_url = reverse('mark-all-notifications-read')

        # Log in the recipient user
        login_response = self.client.post(self.login_url, {
            "email": "recipient@example.com",
            "password": "password123!"
        })
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_notification_created_on_recommendation_in_radius(self):
        # Create recommendation near the recipient (within 25km radius)
        rec = Recommendation.objects.create(
            creator=self.creator,
            category="Food",
            rating=5,
            details="Great food here!",
            latitude=23.8100,
            longitude=90.4120
        )

        # Check notification was created in database
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertEqual(notif.notification_type, 'recommendation')
        self.assertEqual(notif.recommendation, rec)

        # Retrieve notifications via API
        response = self.client.get(self.notifications_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['unread_count'], 1)
        self.assertEqual(len(response.data['notifications']), 1)
        self.assertEqual(response.data['notifications'][0]['title'], "New Recommendation")

    def test_no_notification_if_setting_is_off(self):
        # Recipient turns off recommendation notifications
        self.recipient.notify_recommendations = False
        self.recipient.save()

        # Create recommendation near the recipient
        Recommendation.objects.create(
            creator=self.creator,
            category="Food",
            rating=5,
            details="Great food here!",
            latitude=23.8100,
            longitude=90.4120
        )

        # Check no notification was created
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)

    def test_mark_as_read_endpoints(self):
        # Trigger two notifications
        Recommendation.objects.create(
            creator=self.creator,
            category="Food",
            rating=5,
            details="Great food here!",
            latitude=23.8100,
            longitude=90.4120
        )
        
        Event.objects.create(
            creator=self.creator,
            name="Party",
            location="Dhaka",
            description="Fun times",
            date_time=timezone.now() + timezone.timedelta(days=1),
            latitude=23.8100,
            longitude=90.4120
        )

        # Recipient has 2 notifications
        self.assertEqual(Notification.objects.filter(user=self.recipient, is_read=False).count(), 2)

        # Mark first notification as read
        notif = Notification.objects.filter(user=self.recipient).first()
        read_url = reverse('mark-notification-read', kwargs={'pk': notif.id})
        
        response = self.client.post(read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['unread_count'], 1)

        # Mark all as read
        response = self.client.post(self.read_all_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['unread_count'], 0)
        self.assertEqual(Notification.objects.filter(user=self.recipient, is_read=False).count(), 0)
