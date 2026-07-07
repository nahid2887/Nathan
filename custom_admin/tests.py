from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import SubscriptionPlan

User = get_user_model()

class SubscriptionPlanTests(APITestCase):

    def setUp(self):
        # Create superuser/admin user
        self.admin_user = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="adminpassword123"
        )
        # Create regular user
        self.regular_user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="userpassword123"
        )

        # Generate tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.regular_token = str(RefreshToken.for_user(self.regular_user).access_token)

        # Create a sample plan
        self.plan = SubscriptionPlan.objects.create(
            name="Community Premium",
            price="10.00",
            billing_cycle="monthly",
            discount_offer=10
        )

        # URLs
        self.list_create_url = reverse('subscription-plan-list')
        self.detail_url = reverse('subscription-plan-detail', kwargs={'pk': self.plan.pk})

    def test_unauthenticated_requests_rejected(self):
        # Unauthenticated users cannot view plans
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Unauthenticated users cannot create plans
        data = {
            "name": "New Plan",
            "price": "15.00",
            "billing_cycle": "monthly",
            "discount_offer": 0
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_can_view_plans(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.regular_token}')
        
        # Test List
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Community Premium")

        # Test Retrieve
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Community Premium")

    def test_regular_user_cannot_create_update_delete_plans(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.regular_token}')
        
        # Create attempt
        data = {
            "name": "Pro Premium",
            "price": "19.99",
            "billing_cycle": "yearly",
            "discount_offer": 5
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Update attempt
        response = self.client.put(self.detail_url, {"name": "Updated Plan"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Delete attempt
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_create_plans(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        data = {
            "name": "Super Admin Tier",
            "price": "49.99",
            "billing_cycle": "yearly",
            "discount_offer": 20
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Super Admin Tier")
        self.assertEqual(float(response.data['price']), 49.99)
        self.assertEqual(response.data['discount_offer'], 20)

    def test_admin_user_can_update_plans(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        data = {
            "name": "Community Premium Updated",
            "price": "12.50",
            "billing_cycle": "monthly",
            "discount_offer": 15
        }
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Community Premium Updated")
        self.assertEqual(float(response.data['price']), 12.50)
        self.assertEqual(response.data['discount_offer'], 15)

    def test_admin_user_can_delete_plans(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SubscriptionPlan.objects.filter(pk=self.plan.pk).exists())

    def test_serializer_validation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Test negative price
        data = {
            "name": "Negative Price Plan",
            "price": "-5.00",
            "billing_cycle": "monthly",
            "discount_offer": 10
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

        # Test invalid discount offer percentage (> 100)
        data = {
            "name": "High Discount Plan",
            "price": "10.00",
            "billing_cycle": "monthly",
            "discount_offer": 150
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("discount_offer", response.data)

        # Test invalid discount offer percentage (< 0)
        data = {
            "name": "Negative Discount Plan",
            "price": "10.00",
            "billing_cycle": "monthly",
            "discount_offer": -10
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("discount_offer", response.data)
