from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

from recommendations.models import Recommendation, RecommendationLike, RecommendationComment
from looking_for.models import LookingFor, LookingForLike, LookingForComment
from alert.models import Alert
from accounts.models import Friendship
from notifications.models import Notification

User = get_user_model()

class NotificationTests(APITestCase):

    def setUp(self):
        # Create recipient (creator of the posts, and potential alert receiver)
        self.recipient = User.objects.create_user(
            username="recipient@example.com",
            email="recipient@example.com",
            password="password123!",
            first_name="Recipient User",
            latitude=23.8103,
            longitude=90.4125,
            distance_radius=25
        )
        # Create sender (the one who likes/comments/creates alert)
        self.sender = User.objects.create_user(
            username="sender@example.com",
            email="sender@example.com",
            password="password123!",
            first_name="Sender User",
            latitude=23.8100,
            longitude=90.4120
        )
        
        self.login_url = reverse('login')
        self.notifications_url = reverse('notification-list')
        self.unread_count_url = reverse('notification-unread-count')
        self.read_all_url = reverse('mark-all-notifications-read')
        self.register_token_url = reverse('register-fcm-token')

        # Log in the recipient
        login_response = self.client.post(self.login_url, {
            "email": "recipient@example.com",
            "password": "password123!"
        })
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Create a recommendation owned by recipient
        self.rec = Recommendation.objects.create(
            creator=self.recipient,
            category="Food",
            rating=5,
            details="My fav place"
        )
        
        # Create a looking_for owned by recipient
        self.lf = LookingFor.objects.create(
            creator=self.recipient,
            category="Plumber",
            details="Looking for plumber"
        )

    @patch('notifications.signals.send_push_notification')
    def test_notification_on_recommendation_like(self, mock_push):
        # The sender likes the recipient's recommendation
        RecommendationLike.objects.create(
            recommendation=self.rec,
            user=self.sender
        )

        # Check notification in DB
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertEqual(notif.notification_type, 'recommendation')
        self.assertEqual(notif.title, 'New Like')
        self.assertIn('liked your Recommendation', notif.message)

        # Check FCM push mock was called
        mock_push.assert_called_once()
        args, kwargs = mock_push.call_args
        self.assertEqual(args[0], self.recipient)
        self.assertEqual(args[1], 'New Like')

    @patch('notifications.signals.send_push_notification')
    def test_notification_on_looking_for_comment(self, mock_push):
        # The sender comments on recipient's looking_for
        LookingForComment.objects.create(
            looking_for=self.lf,
            user=self.sender,
            content="I can help you with that!"
        )

        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertEqual(notif.notification_type, 'looking_for')
        self.assertEqual(notif.title, 'New Comment')
        self.assertIn('commented on your Looking For request', notif.message)

        # Check FCM push mock was called
        mock_push.assert_called_once()

    def test_register_fcm_token(self):
        payload = {"fcm_token": "test-device-token-123"}
        response = self.client.post(self.register_token_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify stored token
        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.fcm_token, "test-device-token-123")

    @patch('notifications.signals.send_push_notification')
    def test_mark_as_read_endpoints(self, mock_push):
        # Trigger two notifications by comments/likes
        RecommendationComment.objects.create(
            recommendation=self.rec,
            user=self.sender,
            content="Nice!"
        )
        LookingForLike.objects.create(
            looking_for=self.lf,
            user=self.sender
        )

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

    @patch('notifications.signals.send_push_notification')
    def test_no_self_notification_on_like(self, mock_push):
        # The recipient likes their own recommendation
        RecommendationLike.objects.create(
            recommendation=self.rec,
            user=self.recipient
        )
        
        # Check no notification was created
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)
        mock_push.assert_not_called()

    @patch('notifications.signals.send_push_notification')
    def test_no_self_notification_on_comment(self, mock_push):
        # The recipient comments on their own looking_for request
        LookingForComment.objects.create(
            looking_for=self.lf,
            user=self.recipient,
            content="Self comment response."
        )

        # Check no notification was created
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)
        mock_push.assert_not_called()

    @patch('notifications.push.messaging.send')
    def test_no_crash_on_missing_fcm_token(self, mock_fcm_send):
        # Recipient has no fcm_token set
        self.recipient.fcm_token = None
        self.recipient.save()

        # Try to trigger notification
        RecommendationLike.objects.create(
            recommendation=self.rec,
            user=self.sender
        )

        # The DB notification record should still be created
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        # FCM send should not be called because there's no token
        mock_fcm_send.assert_not_called()

    @patch('notifications.push.messaging.send')
    def test_no_crash_on_fcm_send_exception(self, mock_fcm_send):
        # Recipient has an fcm_token
        self.recipient.fcm_token = "some-invalid-token"
        self.recipient.save()

        # Mock FCM send raising an exception
        mock_fcm_send.side_effect = Exception("FCM server error")

        # Try to trigger notification (should complete successfully without crashing)
        RecommendationComment.objects.create(
            recommendation=self.rec,
            user=self.sender,
            content="This should not crash the request!"
        )

        # The DB notification record should still be created
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)

    @patch('notifications.signals.send_push_notification')
    def test_alert_notification_anyone_privacy_in_radius(self, mock_push):
        # Alert created nearby with 'anyone' privacy
        alert = Alert.objects.create(
            creator=self.sender,
            title="Fire near block C",
            content="Please stay inside.",
            location_name="Dhaka",
            latitude=23.8100,
            longitude=90.4120,
            alert_type="emergency",
            alert_level="critical",
            privacy="anyone"
        )

        # Recipient is nearby and should get notified
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertEqual(notif.notification_type, 'alert')
        self.assertEqual(notif.alert, alert)
        self.assertEqual(notif.title, "New Emergency")
        self.assertIn("posted a new Emergency", notif.message)
        mock_push.assert_called_once()

    @patch('notifications.signals.send_push_notification')
    def test_alert_notification_anyone_privacy_out_radius(self, mock_push):
        # Alert created far away (outside 25km radius)
        Alert.objects.create(
            creator=self.sender,
            title="Fire far away",
            content="Stay inside.",
            location_name="Chittagong",
            latitude=22.3569,
            longitude=91.7832,
            alert_type="emergency",
            alert_level="critical",
            privacy="anyone"
        )

        # Recipient should NOT get notified because it is out of radius
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)
        mock_push.assert_not_called()

    @patch('notifications.signals.send_push_notification')
    def test_alert_notification_friends_privacy(self, mock_push):
        # Alert created with 'friends' privacy
        alert = Alert.objects.create(
            creator=self.sender,
            title="Lost cat",
            content="Help find it.",
            location_name="Dhaka",
            latitude=23.8100,
            longitude=90.4120,
            alert_type="alert",
            alert_level="medium",
            privacy="friends"
        )

        # Recipient is NOT a friend, so should NOT get notified
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)
        mock_push.assert_not_called()

        # Create friendship
        Friendship.objects.create(
            sender=self.recipient,
            receiver=self.sender,
            status='accepted'
        )

        # Create alert again (now they are friends)
        alert2 = Alert.objects.create(
            creator=self.sender,
            title="Lost dog",
            content="Help find it.",
            location_name="Dhaka",
            latitude=23.8100,
            longitude=90.4120,
            alert_type="alert",
            alert_level="medium",
            privacy="friends"
        )

        # Recipient is now a friend and should get notified
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().alert, alert2)
        self.assertEqual(mock_push.call_count, 1)

    @patch('notifications.signals.send_push_notification')
    def test_alert_notification_only_me_privacy(self, mock_push):
        # Alert created with 'only_me' privacy
        Alert.objects.create(
            creator=self.sender,
            title="Private test",
            content="Testing.",
            location_name="Dhaka",
            latitude=23.8100,
            longitude=90.4120,
            alert_type="alert",
            alert_level="medium",
            privacy="only_me"
        )

        # Recipient should NOT get notified
        notifications = Notification.objects.filter(user=self.recipient)
        self.assertEqual(notifications.count(), 0)
        mock_push.assert_not_called()
