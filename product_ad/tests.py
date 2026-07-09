from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from product_ad.models import ProductAd

User = get_user_model()

class ProductAdAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('productad-list')
        
        # Create users
        self.subscribed_user = User.objects.create_user(
            username="subscribed@example.com",
            email="subscribed@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() + timedelta(days=30)
        )
        
        self.subscribed_user_2 = User.objects.create_user(
            username="subscribed2@example.com",
            email="subscribed2@example.com",
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

        self.ad_data = {
            "name": "Super Fast Blender",
            "category": "Appliances",
            "description": "Blends anything in seconds.",
            "phone_number": "+1 (555) 123-4567",
            "email_address": "sales@blender.com",
            "website": "https://www.superblender.com",
            "latitude": "40.7128000000000000",
            "longitude": "-74.0060000000000000",
            "location_name": "New York, NY",
            "business_hours": {
                "days": ["M", "T", "W", "T", "F"],
                "from": "09:00",
                "to": "17:00"
            }
        }

    def obtain_token(self, email):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": "testpassword123!"
        })
        return response.data['access']

    def test_subscribed_user_can_list_product_ads(self):
        ProductAd.objects.create(
            creator=self.subscribed_user,
            name="Blender Ad",
            category="Appliances",
            description="Details",
            phone_number="123",
            email_address="sales@blender.com",
            latitude=0.0,
            longitude=0.0,
            location_name="Here"
        )
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_subscribed_user_can_create_product_ad(self):
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.ad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.ad_data['name'])
        self.assertEqual(response.data['creator']['email'], "subscribed@example.com")

    def test_unsubscribed_user_cannot_list_product_ads(self):
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsubscribed_user_cannot_create_product_ad(self):
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.ad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_user_cannot_list_product_ads(self):
        token = self.obtain_token("expired@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.expired_user.refresh_from_db()
        self.assertFalse(self.expired_user.is_subscribed)

    def test_expired_user_cannot_create_product_ad(self):
        token = self.obtain_token("expired@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.list_create_url, self.ad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_update_and_delete_own_product_ad(self):
        # Create an ad owned by subscribed_user
        ad = ProductAd.objects.create(
            creator=self.subscribed_user,
            name="Original Name",
            category="Appliances",
            description="Details",
            phone_number="123",
            email_address="sales@blender.com",
            latitude=0.0,
            longitude=0.0,
            location_name="Here"
        )
        
        detail_url = reverse('productad-detail', args=[ad.id])
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Update
        response = self.client.patch(detail_url, {"name": "New Name"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "New Name")
        
        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_creator_cannot_update_or_delete_others_product_ad(self):
        # Create an ad owned by subscribed_user
        ad = ProductAd.objects.create(
            creator=self.subscribed_user,
            name="Blender Ad",
            category="Appliances",
            description="Details",
            phone_number="123",
            email_address="sales@blender.com",
            latitude=0.0,
            longitude=0.0,
            location_name="Here"
        )
        
        detail_url = reverse('productad-detail', args=[ad.id])
        token = self.obtain_token("subscribed2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try update -> Forbidden
        response = self.client.patch(detail_url, {"name": "New Name"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try delete -> Forbidden
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
