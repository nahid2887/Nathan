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


class DealNearbyAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            latitude=-33.8688,
            longitude=151.2093,
            distance_radius=25.0
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            latitude=-33.8700,
            longitude=151.2100
        )
        self.user_no_loc = User.objects.create_user(
            username="noloc@example.com",
            email="noloc@example.com",
            password="password123!"
        )

        from deal.models import Deal
        # Deal nearby (Sydney, ~0.15km away)
        self.nearby_deal = Deal.objects.create(
            creator=self.user2,
            title="Sydney Bistro Deal",
            category="Food",
            deal_type="Percentage",
            description="20% off at Sydney Bistro",
            business_name="Sydney Bistro",
            phone_number="12345",
            latitude=-33.8700,
            longitude=151.2100,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        # Deal far away (Melbourne, ~700km away)
        self.far_deal = Deal.objects.create(
            creator=self.user2,
            title="Melbourne Retail Deal",
            category="Retail",
            deal_type="Percentage",
            description="30% off at Melbourne Retail",
            business_name="Melbourne Retail",
            phone_number="54321",
            latitude=-37.8136,
            longitude=144.9631,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        # Deal from user1 itself (should be excluded)
        self.own_deal = Deal.objects.create(
            creator=self.user1,
            title="My Own Deal",
            category="Food",
            deal_type="Percentage",
            description="10% off my own",
            business_name="My Shop",
            phone_number="999",
            latitude=-33.8688,
            longitude=151.2093,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        self.nearby_url = reverse('deal-nearby')

    def obtain_token(self, email):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": "password123!"
        })
        return response.data['access']

    def test_get_nearby_deals_success(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.nearby_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Returns all deals sorted by distance (nearest first, including own deal)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['title'], "My Own Deal")
        self.assertEqual(response.data[1]['title'], "Sydney Bistro Deal")
        self.assertEqual(response.data[2]['title'], "Melbourne Retail Deal")
        self.assertIsNotNone(response.data[0]['distance_km'])
        self.assertEqual(response.data[0]['distance_km'], 0.0)

    def test_get_nearby_deals_with_larger_distance(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.nearby_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['title'], "My Own Deal")
        self.assertEqual(response.data[1]['title'], "Sydney Bistro Deal")
        self.assertEqual(response.data[2]['title'], "Melbourne Retail Deal")

    def test_get_nearby_deals_filter_by_category(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Filter by Food (should return My Own Deal and Sydney Bistro Deal)
        response = self.client.get(f"{self.nearby_url}?category=Food")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], "My Own Deal")
        self.assertEqual(response.data[1]['title'], "Sydney Bistro Deal")

        # Filter by Retail (should return Melbourne Retail Deal)
        response = self.client.get(f"{self.nearby_url}?category=Retail")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Melbourne Retail Deal")

    def test_get_nearby_deals_filter_by_search(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Search for "Melbourne"
        response = self.client.get(f"{self.nearby_url}?search=Melbourne")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Melbourne Retail Deal")

    def test_get_nearby_deals_no_location_error(self):
        token = self.obtain_token("noloc@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.nearby_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User location coordinates", response.data['message'])

    def test_get_nearby_deals_invalid_distance_param_type(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(f"{self.nearby_url}?distance=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid distance", response.data['message'])

    def test_get_nearby_deals_negative_distance(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(f"{self.nearby_url}?distance=-50")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Distance cannot be negative", response.data['message'])

    def test_get_nearby_deals_empty_whitespace_filtering(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # empty search parameter shouldn't filter out deals
        response = self.client.get(f"{self.nearby_url}?search=   &category=   ")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['title'], "My Own Deal")

    def test_get_nearby_deals_unauthenticated(self):
        # Clear credentials
        self.client.credentials()
        response = self.client.get(self.nearby_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DealAnalyticsAndSavedAPITests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            latitude=-33.8688,
            longitude=151.2093
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            latitude=-33.8700,
            longitude=151.2100
        )

        from deal.models import Deal
        self.deal = Deal.objects.create(
            creator=self.user1,
            title="Sydney Bistro Deal",
            category="Food",
            deal_type="Percentage",
            description="20% off at Sydney Bistro",
            business_name="Sydney Bistro",
            phone_number="1234567890",
            address="123 Sydney St",
            latitude=-33.8700,
            longitude=151.2100,
            location_name="Sydney Central",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        self.detail_url = reverse('deal-detail', kwargs={'pk': self.deal.id})
        self.click_call_url = reverse('deal-click-call', kwargs={'pk': self.deal.id})
        self.click_directions_url = reverse('deal-click-directions', kwargs={'pk': self.deal.id})
        self.click_view_url = reverse('deal-click-view', kwargs={'pk': self.deal.id})
        self.save_url = reverse('deal-save-deal', kwargs={'pk': self.deal.id})
        self.unsave_url = reverse('deal-unsave-deal', kwargs={'pk': self.deal.id})
        self.saved_url = reverse('deal-saved')

    def obtain_token(self, email):
        login_url = reverse('login')
        response = self.client.post(login_url, {
            "email": email,
            "password": "password123!"
        })
        return response.data['access']

    def test_views_count_increment_by_other_user(self):
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Initially views is 0
        self.assertEqual(self.deal.views_count, 0)

        # Retrieve the deal as user2
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify count incremented in DB
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.views_count, 1)
        self.assertNotIn('views_count', response.data)

    def test_views_count_no_increment_by_creator(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Initially views is 0
        self.assertEqual(self.deal.views_count, 0)

        # Retrieve the deal as creator (user1)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify count is still 0
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.views_count, 0)
        self.assertEqual(response.data['views_count'], 0)

    def test_call_clicks_tracking(self):
        # 1. Click by other user (should increment)
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        response = self.client.post(self.click_call_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], "1234567890")

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.call_clicks_count, 1)

        # 2. Click by creator (should not increment)
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response = self.client.post(self.click_call_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], "1234567890")

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.call_clicks_count, 1)

    def test_directions_clicks_tracking(self):
        # 1. Click by other user (should increment)
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        response = self.client.post(self.click_directions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['address'], "123 Sydney St")
        self.assertEqual(response.data['location_name'], "Sydney Central")
        self.assertEqual(float(response.data['latitude']), -33.8700)
        self.assertEqual(float(response.data['longitude']), 151.2100)

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.directions_clicks_count, 1)

        # 2. Click by creator (should not increment)
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response = self.client.post(self.click_directions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.directions_clicks_count, 1)

    def test_save_unsave_and_saved_list_flow(self):
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        # Initially not saved
        response = self.client.get(self.detail_url)
        self.assertFalse(response.data['is_saved'])
        self.assertNotIn('saves_count', response.data)

        # 1. Save deal -> Success
        response = self.client.post(self.save_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.saves_count, 1)

        # Check detail serialization for other user shows is_saved=True, saves_count hidden
        response = self.client.get(self.detail_url)
        self.assertTrue(response.data['is_saved'])
        self.assertNotIn('saves_count', response.data)

        # Check detail serialization for creator shows saves_count = 1
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        creator_response = self.client.get(self.detail_url)
        self.assertEqual(creator_response.data['saves_count'], 1)

        # Switch back to user2 credentials for subsequent tests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        # 2. View saved list (should contain this deal)
        response = self.client.get(self.saved_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Sydney Bistro Deal")

        # 3. Unsave deal -> Success
        response = self.client.post(self.unsave_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.saves_count, 0)

        # Saved list is now empty
        response = self.client.get(self.saved_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_cannot_save_own_deal(self):
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response = self.client.post(self.save_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("cannot save your own deal", response.data['message'])

    def test_click_view_increment_by_other_user(self):
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Initially views is 0
        self.assertEqual(self.deal.views_count, 0)

        # Call POST click-view as user2
        response = self.client.post(self.click_view_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('views_count', response.data)
        self.assertEqual(response.data['title'], "Sydney Bistro Deal")
        self.assertEqual(response.data['description'], "20% off at Sydney Bistro")

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.views_count, 1)

    def test_click_view_no_increment_by_creator(self):
        token = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Initially views is 0
        self.assertEqual(self.deal.views_count, 0)

        # Call POST click-view as creator
        response = self.client.post(self.click_view_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['views_count'], 0)
        self.assertEqual(response.data['title'], "Sydney Bistro Deal")

        self.deal.refresh_from_db()
        self.assertEqual(self.deal.views_count, 0)

    def test_list_deals_search_filter(self):
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        deals_url = reverse('deal-list')

        # Query with search matching "Sydney" -> Should return the deal
        response = self.client.get(f"{deals_url}?search=Sydney")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Sydney Bistro Deal")

        # Query with search matching "Melbourne" -> Should return 0 deals
        response = self.client.get(f"{deals_url}?search=Melbourne")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_creator_impressions_count_calculation(self):
        # Create a second deal for user1
        from deal.models import Deal
        another_deal = Deal.objects.create(
            creator=self.user1,
            title="Second Deal",
            category="Food",
            deal_type="Percentage",
            description="Second",
            business_name="Second Shop",
            phone_number="12345",
            latitude=-33.8700,
            longitude=151.2100,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        # Set views counts
        self.deal.views_count = 10
        self.deal.save()
        another_deal.views_count = 5
        another_deal.save()

        # 1. Query deal detail as user2 (other user) -> impressions_count should be hidden
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('impressions_count', response.data['creator'])

        # 2. Query deal detail as user1 (creator) -> impressions_count should be visible and equal 16 (11 + 5)
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['creator']['impressions_count'], 16)

    def test_clicks_count_field(self):
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        # Non-creator gets detail -> clicks_count should be hidden
        response = self.client.get(self.detail_url)
        self.assertNotIn('clicks_count', response.data)

        # Record a call click
        self.client.post(self.click_call_url)
        # Record a directions click
        self.client.post(self.click_directions_url)

        # Creator gets detail -> clicks_count should be 2
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['clicks_count'], 2)

    def test_list_deals_search_filter_whitespace_and_empty(self):
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        deals_url = reverse('deal-list')

        # Whitespace-only search query should return the deal and not filter it out
        response = self.client.get(f"{deals_url}?search=   ")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Sydney Bistro Deal")

    def test_list_deals_search_special_characters(self):
        token = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        deals_url = reverse('deal-list')

        # Special characters search query should safely return 0 matching deals without crashing
        response = self.client.get(f"{deals_url}?search=!@#$%^&*()")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_list_deals_unauthenticated(self):
        # Clear credentials
        self.client.credentials()
        deals_url = reverse('deal-list')

        response = self.client.get(deals_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_deals_shows_creator_impressions_count(self):
        # Create another deal by user1
        from deal.models import Deal
        another_deal = Deal.objects.create(
            creator=self.user1,
            title="Second Deal",
            category="Food",
            deal_type="Percentage",
            description="Second",
            business_name="Second Shop",
            phone_number="12345",
            latitude=-33.8700,
            longitude=151.2100,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        self.deal.views_count = 8
        self.deal.save()
        another_deal.views_count = 4
        another_deal.save()

        # 1. List deals as user2 (other user) -> impressions_count should be hidden
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        deals_url = reverse('deal-list')

        response = self.client.get(deals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('impressions_count', response.data[0]['creator'])

        # 2. List deals as user1 (creator) -> impressions_count should be visible and equal 12
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response = self.client.get(deals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['creator']['impressions_count'], 12)

    def test_business_analytics_endpoint(self):
        # Create a second deal for user1
        from deal.models import Deal
        another_deal = Deal.objects.create(
            creator=self.user1,
            title="Second Deal",
            category="Food",
            deal_type="Percentage",
            description="Second",
            business_name="Second Shop",
            phone_number="12345",
            latitude=-33.8700,
            longitude=151.2100,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            is_active=True
        )

        # Set specific analytics counters on both deals
        self.deal.views_count = 10
        self.deal.call_clicks_count = 4
        self.deal.directions_clicks_count = 6
        self.deal.saves_count = 2
        self.deal.save()

        another_deal.views_count = 20
        another_deal.call_clicks_count = 8
        another_deal.directions_clicks_count = 12
        another_deal.saves_count = 4
        another_deal.save()

        # Query analytics as user1 (creator)
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        analytics_url = reverse('deal-analytics')
        response = self.client.get(analytics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check aggregate calculations
        self.assertEqual(response.data['total_views'], 30)
        self.assertEqual(response.data['total_phone_call_taps'], 12)
        self.assertEqual(response.data['total_directions_clicks'], 18)
        self.assertEqual(response.data['total_saved_deals'], 6)

        # Check that individual deal performance metrics are serialized and visible for creator
        self.assertEqual(len(response.data['deals_performance']), 2)
        # Note: ordered by created_at desc, so another_deal is first
        self.assertEqual(response.data['deals_performance'][0]['views_count'], 20)
        self.assertEqual(response.data['deals_performance'][0]['call_clicks_count'], 8)
        self.assertEqual(response.data['deals_performance'][1]['views_count'], 10)
        self.assertEqual(response.data['deals_performance'][1]['call_clicks_count'], 4)

        # Query analytics as user2 (who has 0 deals created)
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        response2 = self.client.get(analytics_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['total_views'], 0)
        self.assertEqual(len(response2.data['deals_performance']), 0)

    def test_payment_success_verification_deal_plan(self):
        from unittest.mock import patch
        from deal.models import DealPlan
        from accounts.models import User

        plan = DealPlan.objects.create(
            name="Growth Plan",
            price="39.00",
            billing_cycle="monthly",
            active_deals_limit=5
        )

        token = self.obtain_token(self.user1.email)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            class MockSession:
                id = 'cs_test_deal_123'
                payment_status = 'paid'
                metadata = {
                    'user_id': self.user1.id,
                    'plan_id': plan.id,
                    'plan_type': 'deal'
                }
            mock_retrieve.return_value = MockSession()

            success_url = reverse('payment_success')
            response = self.client.get(f"{success_url}?session_id=cs_test_deal_123")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
            self.assertTrue(response.data['is_subscribed'])  # returns user.is_deal_subscribed for deal type plan

            # Check DB updated
            self.user1.refresh_from_db()
            self.assertTrue(self.user1.is_deal_subscribed)
            self.assertEqual(self.user1.current_deal_plan, plan)

    def test_deactivate_deal(self):
        # 1. Try to deactivate as a non-creator (user2) -> should return 403 Forbidden
        token2 = self.obtain_token("user2@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        deactivate_url = reverse('deal-deactivate', kwargs={'pk': self.deal.id})
        response = self.client.post(deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Deactivate as the creator (user1) -> should succeed and set is_active to False
        token1 = self.obtain_token("user1@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')

        response2 = self.client.post(deactivate_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertFalse(response2.data['is_active'])

        # Verify in database
        self.deal.refresh_from_db()
        self.assertFalse(self.deal.is_active)

