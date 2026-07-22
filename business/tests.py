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
            creator=self.unsubscribed_user,  # Created by another user
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

    def test_unsubscribed_user_cannot_retrieve_business_details(self):
        biz = Business.objects.create(
            creator=self.subscribed_user,
            name="Green Valley",
            category="Landscaping",
            description="Special",
            phone_number="123",
            email_address="hello@business.com",
            latitude=0.0,
            longitude=0.0
        )
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        detail_url = reverse('business-detail', kwargs={'pk': biz.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_non_creator_subscriber_cannot_edit_business(self):
        biz = Business.objects.create(
            creator=self.subscribed_user,
            name="Valley Landscaping",
            category="Landscaping",
            description="Special",
            phone_number="123",
            email_address="hello@business.com",
            latitude=0.0,
            longitude=0.0
        )
        user_b = User.objects.create_user(
            username="user_b@example.com",
            email="user_b@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() + timedelta(days=30)
        )
        token = self.obtain_token("user_b@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        detail_url = reverse('business-detail', kwargs={'pk': biz.id})
        response = self.client.put(detail_url, self.business_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_businesses(self):
        self.client.credentials()
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_businesses_excludes_own(self):
        # Create user's own business
        Business.objects.create(
            creator=self.subscribed_user,
            name="My Own Biz",
            category="Retail",
            description="Details",
            phone_number="123",
            email_address="me@example.com",
            latitude=0.0,
            longitude=0.0
        )
        # Create other user's business
        Business.objects.create(
            creator=self.unsubscribed_user,
            name="Other User Biz",
            category="Retail",
            description="Details",
            phone_number="456",
            email_address="other@example.com",
            latitude=0.0,
            longitude=0.0
        )

        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return Other User Biz (1 listing)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Other User Biz")

    def test_my_businesses_returns_only_own(self):
        # Create user's own business
        biz = Business.objects.create(
            creator=self.subscribed_user,
            name="My Own Biz",
            category="Retail",
            description="Details",
            phone_number="123",
            email_address="me@example.com",
            latitude=0.0,
            longitude=0.0,
            views_count=5,
            directions_clicks_count=3
        )
        # Create other user's business
        Business.objects.create(
            creator=self.unsubscribed_user,
            name="Other User Biz",
            category="Retail",
            description="Details",
            phone_number="456",
            email_address="other@example.com",
            latitude=0.0,
            longitude=0.0
        )

        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        my_url = reverse('business-my-businesses')
        response = self.client.get(my_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return My Own Biz (1 listing)
        self.assertEqual(len(response.data['businesses']), 1)
        self.assertEqual(response.data['businesses'][0]['name'], "My Own Biz")
        # Check aggregate analytics
        self.assertEqual(response.data['total_views'], 5)
        self.assertEqual(response.data['total_clicks'], 3)
        self.assertEqual(response.data['total_engagement'], 8)

    def test_click_view_and_click_directions_recording(self):
        # Create a business owned by self.subscribed_user
        biz = Business.objects.create(
            creator=self.subscribed_user,
            name="Green Valley",
            category="Landscaping",
            description="Special",
            phone_number="123",
            email_address="hello@business.com",
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York, NY"
        )

        user_b = User.objects.create_user(
            username="user_b@example.com",
            email="user_b@example.com",
            password="testpassword123!",
            is_subscribed=True,
            subscription_expiry=timezone.now() + timedelta(days=30)
        )
        token_b = self.obtain_token("user_b@example.com")
        token_creator = self.obtain_token("subscribed@example.com")

        click_view_url = reverse('business-click-view', kwargs={'pk': biz.id})
        click_directions_url = reverse('business-click-directions', kwargs={'pk': biz.id})

        # 1. Accessing click-view as non-creator (user_b) -> should increment views_count
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')
        response = self.client.post(click_view_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # For non-creator, views_count field should be hidden in serializer output
        self.assertNotIn('views_count', response.data)

        # Retrieve as creator -> views_count should be visible and equal to 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_creator}')
        detail_url = reverse('business-detail', kwargs={'pk': biz.id})
        response_detail = self.client.get(detail_url)
        self.assertEqual(response_detail.data['views_count'], 1)

        # 2. Accessing click-view as creator -> should NOT increment views_count
        response = self.client.post(click_view_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['views_count'], 1)  # Still 1

        # 3. Accessing click-directions as non-creator (user_b) -> should increment directions_clicks_count
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')
        response = self.client.post(click_directions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location_name'], "New York, NY")
        self.assertEqual(float(response.data['latitude']), 40.7128)

        # Retrieve as creator -> directions_clicks_count should be visible and equal to 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_creator}')
        response_detail = self.client.get(detail_url)
        self.assertEqual(response_detail.data['directions_clicks_count'], 1)

        # 4. Accessing click-directions as creator -> should NOT increment directions_clicks_count
        response = self.client.post(click_directions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_detail = self.client.get(detail_url)
        self.assertEqual(response_detail.data['directions_clicks_count'], 1)  # Still 1




class BusinessProfileAPITests(APITestCase):

    def setUp(self):
        self.profile_url = reverse('business-profile')
        
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

        self.profile_data = {
            "name": "Bondi Kitchen & Living",
            "category": "Retail",
            "about": "Bondi Kitchen & Living is your premier destination for high-quality, sustainable home goods.",
            "phone_number": "+61 2 9123 4567",
            "website": "https://bondikitchenliving.com.au",
            "service_area": "Bondi, Bronte, Tamarama",
            "latitude": "-33.8915000000000000",
            "longitude": "151.2767000000000000",
            "location_name": "Bondi",
            "business_hours": {
                "Mon-Fri": "9:00 AM - 6:00 PM",
                "Saturday": "10:00 AM - 5:00 PM",
                "Sunday": "Closed"
            }
        }

    def obtain_token(self, email):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": "testpassword123!"
        })
        return response.data['access']

    def test_subscribed_user_can_manage_profile(self):
        token = self.obtain_token("subscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 1. Retrieve profile before creation -> 404
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Create profile -> 201
        response = self.client.post(self.profile_url, self.profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Bondi Kitchen & Living")
        self.assertEqual(response.data['user']['email'], "subscribed@example.com")

        # 3. Create profile again -> 400 (only single profile allowed)
        response = self.client.post(self.profile_url, self.profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Retrieve profile -> 200
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Bondi Kitchen & Living")

        # 5. Update profile (PUT) -> 200
        updated_data = self.profile_data.copy()
        updated_data['name'] = "New Bondi Name"
        response = self.client.put(self.profile_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "New Bondi Name")

        # 6. Delete profile -> 204
        response = self.client.delete(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 7. Retrieve after deletion -> 404
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unsubscribed_user_cannot_access_profile(self):
        token = self.obtain_token("unsubscribed@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(self.profile_url, self.profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_user_cannot_access_profile(self):
        token = self.obtain_token("expired@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(self.profile_url, self.profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

