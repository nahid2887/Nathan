from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from deal.models import DealPlan

User = get_user_model()

class DealPlanAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.superadmin = User.objects.create_superuser(
            username="super@example.com",
            email="super@example.com",
            password="adminpassword123!"
        )
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="userpassword123!"
        )

        self.deal_plan_data = {
            "name": "Starter",
            "price": "19.00",
            "billing_cycle": "monthly",
            "discount_offer": 0,
            "active_deals_limit": 1,
            "badge_text": "New Business",
            "is_most_popular": False,
            "features": ["1 active deal", "Business profile", "Basic analytics"]
        }

        self.list_create_url = reverse('deal-plan-list')

    def obtain_token(self, email, password):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": password
        })
        return response.data['access']

    def test_unauthenticated_user_cannot_view_or_manage_plans(self):
        # GET List
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # POST Create
        response = self.client.post(self.list_create_url, self.deal_plan_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_can_view_plans_but_cannot_manage(self):
        # Create a plan as superadmin
        plan = DealPlan.objects.create(**self.deal_plan_data)

        token = self.obtain_token("user@example.com", "userpassword123!")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # GET List -> 200 OK
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['plans']), 1)

        # GET Detail -> 200 OK
        detail_url = reverse('deal-plan-detail', kwargs={'pk': plan.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Starter")

        # POST Create -> 403 Forbidden
        response = self.client.post(self.list_create_url, self.deal_plan_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PUT Update -> 403 Forbidden
        response = self.client.put(detail_url, self.deal_plan_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE -> 403 Forbidden
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_manage_plans(self):
        token = self.obtain_token("super@example.com", "adminpassword123!")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # POST Create -> 201 Created
        response = self.client.post(self.list_create_url, self.deal_plan_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Starter")
        plan_id = response.data['id']

        # PUT Update -> 200 OK
        detail_url = reverse('deal-plan-detail', kwargs={'pk': plan_id})
        updated_data = self.deal_plan_data.copy()
        updated_data['name'] = "Growth"
        updated_data['price'] = "39.00"
        response = self.client.put(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Growth")
        self.assertEqual(response.data['price'], "39.00")

        # DELETE -> 204 No Content
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class DealSubscriptionTests(APITestCase):

    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            username="super@example.com",
            email="super@example.com",
            password="adminpassword123!"
        )
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="userpassword123!"
        )
        self.plan = DealPlan.objects.create(
            name="Growth",
            price="39.00",
            billing_cycle="monthly",
            active_deals_limit=5
        )

        self.subscribe_url = reverse('deal-plans-subscribe')
        self.my_subscription_url = reverse('deal-plans-my-subscription')
        self.verify_url = reverse('deal-plans-verify')

    def obtain_token(self, email, password):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": password
        })
        return response.data['access']

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_checkout_create):
        # Mock Stripe
        mock_checkout_create.return_value.url = "https://checkout.stripe.com/test"
        mock_checkout_create.return_value.id = "cs_test_deal_123"

        token = self.obtain_token("user@example.com", "userpassword123!")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        payload = {"plan_id": self.plan.id}
        response = self.client.post(self.subscribe_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['checkout_url'], "https://checkout.stripe.com/test")
        self.assertEqual(response.data['session_id'], "cs_test_deal_123")

    @patch('stripe.checkout.Session.retrieve')
    def test_verify_checkout_session_success(self, mock_session_retrieve):
        # Mock Session
        class MockSession:
            payment_status = 'paid'
            metadata = {
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'plan_type': 'deal'
            }
        mock_session_retrieve.return_value = MockSession()

        # Call Verify endpoint (allow any permissions)
        response = self.client.get(f"{self.verify_url}?session_id=cs_test_deal_123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['is_deal_subscribed'])

        # Verify DB changes
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deal_subscribed)
        self.assertEqual(self.user.current_deal_plan, self.plan)
        self.assertIsNotNone(self.user.deal_subscription_expiry)

    from django.test import override_settings

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test_secret')
    def test_stripe_webhook_deal_plan_activation(self):
        # We call the stripe webhook endpoint with a checkout.session.completed event for a deal plan
        webhook_url = reverse('stripe_webhook')
        payload = {
            "id": "evt_test_webhook_deal",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_deal_webhook",
                    "payment_status": "paid",
                    "metadata": {
                        "user_id": self.user.id,
                        "plan_id": self.plan.id,
                        "plan_type": "deal"
                    }
                }
            }
        }
        
        # Clear credentials for webhook (it's unauthenticated)
        self.client.credentials()
        response = self.client.post(webhook_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify DB changes
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deal_subscribed)
        self.assertEqual(self.user.current_deal_plan, self.plan)
        self.assertIsNotNone(self.user.deal_subscription_expiry)

    def test_my_subscription_expiry_check(self):
        # Set subscription as expired
        self.user.is_deal_subscribed = True
        self.user.deal_subscription_expiry = timezone.now() - timedelta(days=1)
        self.user.current_deal_plan = self.plan
        self.user.save()

        token = self.obtain_token("user@example.com", "userpassword123!")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Call own subscription detail view -> triggers dynamic check and resets to false
        response = self.client.get(self.my_subscription_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_deal_subscribed'])

        # Verify DB reflects the change
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deal_subscribed)


class DealCreationLimitTests(APITestCase):

    def setUp(self):
        # Plans
        self.starter_plan = DealPlan.objects.create(name="Starter", price=19.00, active_deals_limit=1)
        self.growth_plan = DealPlan.objects.create(name="Growth", price=39.00, active_deals_limit=5)
        self.premium_plan = DealPlan.objects.create(name="Premium", price=79.00, active_deals_limit=None) # Unlimited

        # User
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="password123!"
        )

        self.deals_url = reverse('deal-list')

        # Generic deal payload
        self.deal_payload = {
            "title": "50% off Landscaping",
            "category": "Home Services",
            "deal_type": "Percentage",
            "description": "50% off on all home gardening services.",
            "business_name": "Green Valley Gardening",
            "business_type": "Physical Location",
            "phone_number": "+1 (555) 123-4567",
            "start_date": timezone.now().date(),
            "end_date": timezone.now().date() + timedelta(days=7)
        }

    def obtain_token(self):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": "user@example.com",
            "password": "password123!"
        })
        return response.data['access']

    def test_unsubscribed_user_cannot_create_deal(self):
        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(self.deals_url, self.deal_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active deal subscription is required", str(response.data))

    def test_starter_deal_plan_limit_of_one(self):
        # Subscribe user to Starter
        self.user.is_deal_subscribed = True
        self.user.deal_subscription_expiry = timezone.now() + timedelta(days=30)
        self.user.current_deal_plan = self.starter_plan
        self.user.save()

        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create first deal -> Success
        response = self.client.post(self.deals_url, self.deal_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create second deal -> Blocked
        response = self.client.post(self.deals_url, self.deal_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limited to 1 active deal", str(response.data))

    def test_growth_deal_plan_limit_of_five(self):
        # Subscribe user to Growth
        self.user.is_deal_subscribed = True
        self.user.deal_subscription_expiry = timezone.now() + timedelta(days=30)
        self.user.current_deal_plan = self.growth_plan
        self.user.save()

        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create 5 deals -> Success
        for i in range(5):
            payload = self.deal_payload.copy()
            payload['title'] = f"Deal #{i+1}"
            response = self.client.post(self.deals_url, payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create 6th deal -> Blocked
        response = self.client.post(self.deals_url, self.deal_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limited to 5 active deal", str(response.data))

    def test_premium_deal_plan_unlimited(self):
        # Subscribe user to Premium (unlimited)
        self.user.is_deal_subscribed = True
        self.user.deal_subscription_expiry = timezone.now() + timedelta(days=30)
        self.user.current_deal_plan = self.premium_plan
        self.user.save()

        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create 10 deals -> Success
        for i in range(10):
            payload = self.deal_payload.copy()
            payload['title'] = f"Premium Deal #{i+1}"
            response = self.client.post(self.deals_url, payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_expired_deals_not_counted_in_limit(self):
        # Subscribe user to Starter (limit = 1)
        self.user.is_deal_subscribed = True
        self.user.deal_subscription_expiry = timezone.now() + timedelta(days=30)
        self.user.current_deal_plan = self.starter_plan
        self.user.save()

        # Create an already expired deal directly in DB
        from deal.models import Deal
        Deal.objects.create(
            creator=self.user,
            title="Expired Deal",
            category="Home Services",
            deal_type="Percentage",
            description="Expired",
            business_name="Biz",
            phone_number="123",
            start_date=timezone.now().date() - timedelta(days=10),
            end_date=timezone.now().date() - timedelta(days=2) # Expired
        )

        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create another deal -> Success (because the expired one does not count)
        response = self.client.post(self.deals_url, self.deal_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_deals_filter_by_category(self):
        # Create some deals
        from deal.models import Deal
        Deal.objects.create(
            creator=self.user,
            title="Burger Promo",
            category="Food",
            deal_type="Buy One Get One",
            description="BOGO Burger",
            business_name="Burger Joint",
            phone_number="123",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=1)
        )
        Deal.objects.create(
            creator=self.user,
            title="Shirt Promo",
            category="Retail",
            deal_type="Percentage",
            description="Discount",
            business_name="Fashion Shop",
            phone_number="456",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=1)
        )

        token = self.obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Query all
        response = self.client.get(self.deals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Filter by Food
        response = self.client.get(f"{self.deals_url}?category=Food")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Burger Promo")

        # Filter by food (case-insensitive)
        response = self.client.get(f"{self.deals_url}?category=food")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Burger Promo")

        # Filter by Retail
        response = self.client.get(f"{self.deals_url}?category=Retail")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Shirt Promo")

