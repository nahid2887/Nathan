from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from custom_admin.models import SubscriptionPlan
from business.models import Business

User = get_user_model()

class BusinessAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('business-list')
        
        # Create users
        self.subscribed_user = User.objects.create_user(
            username="subscribed@example.com",
            email="subscribed@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() + timedelta(days=30)
        )
        
        self.unsubscribed_user = User.objects.create_user(
            username="unsubscribed@example.com",
            email="unsubscribed@example.com",
            password="testpassword123!",
            is_subscribed=False
        )

        self.expired_user = User.objects.create_user(
            username="expired@example.com",
            email="expired@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() - timedelta(days=1)
        )

        self.business_data = {
            "name": "Green Valley Landscaping",
            "category": "Landscaping",
            "description": "Tell the neighborhood what makes your business special.",
            "phone_number": "+1 (555) 000-0000",
            "email_address": "hello@business.com",
            "website": "https://www.yourbusiness.com",
            "latitude": "40.7128000000000000",
            "longitude": "-74.0060000000000000",
            "location_name": "New York, NY",
            "business_hours": {
                "days": ["M", "T", "W"],
                "from": "09:00",
                "to": "18:00"
            }
        }

    def obtain_token(self, email):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": "testpassword123!"
        })
        return response.data['access']

    def test_subscribed_user_can_list_businesses(self):
        Business.objects.create(
            creator=self.subscribed_user,
            name="Subscribed Biz",
            category="Services",
            description="Details",
            phone_number="123",
            email_address="biz@example.com",
            latitude=0.0,
            longitude=0.0,
            location_name="Here"
        )
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_subscribed_user_can_create_business(self):
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.business_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.business_data['name'])
        self.assertEqual(response.data['creator']['email'], "subscribed@example.com")

    def test_unsubscribed_user_cannot_list_businesses(self):
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsubscribed_user_cannot_create_business(self):
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.business_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_user_cannot_list_businesses(self):
        token = self.obtain_token("expired@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.expired_user.refresh_from_db()
        self.assertFalse(self.expired_user.is_subscribed)

    def test_expired_user_cannot_create_business(self):
        token = self.obtain_token("expired@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.business_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_rating_and_restrictions(self):
        business = Business.objects.create(
            creator=self.subscribed_user,
            name="Test Biz",
            category="Food",
            description="Good food",
            phone_number="111",
            email_address="test@biz.com",
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York"
        )

        # 1. Initial average rating is 0.0
        self.assertEqual(business.average_rating, 0.0)
        self.assertEqual(business.ratings_count, 0)

        # Create another subscribed user (non-owner) to leave a rating
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() + timedelta(days=30),
            latitude=40.7128,
            longitude=-74.0060
        )
        token_other = self.obtain_token("other@example.com")

        # 2. Rate the business via the API as other_user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_other}')
        rate_url = reverse('business-rate', args=[business.id])
        
        response = self.client.post(rate_url, {"rating": 5, "comment": "Amazing!"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)

        # Check updated average rating
        business.refresh_from_db()
        self.assertEqual(business.average_rating, 5.0)
        self.assertEqual(business.ratings_count, 1)

        # 3. Try to rate the business as the owner (subscribed_user)
        token_owner = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_owner}')
        
        response = self.client.post(rate_url, {"rating": 4, "comment": "Great!"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Check distance calculation in listing
        far_business = Business.objects.create(
            creator=self.subscribed_user,
            name="Sydney Biz",
            category="Retail",
            description="Far away",
            phone_number="222",
            email_address="sydney@biz.com",
            latitude=-33.8688,
            longitude=151.2093,
            location_name="Sydney"
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_other}')
        detail_url = reverse('business-detail', args=[far_business.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['distance_km'], 15000)

