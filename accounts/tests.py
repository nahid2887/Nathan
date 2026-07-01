from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AccountsAPITests(APITestCase):

    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.change_password_url = reverse('change_password')
        self.profile_url = reverse('profile')
        self.forgot_password_url = reverse('forgot_password')
        self.verify_otp_url = reverse('verify_otp')
        self.reset_password_url = reverse('reset_password')

        self.user_data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123!",
            "confirm_password": "testpassword123!"
        }
        self.user = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="oldpassword123!",
            first_name="Existing User"
        )

    def test_register_user_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

    def test_register_user_duplicate_email(self):
        # Register once
        self.client.post(self.register_url, self.user_data)
        # Register again with same email
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('email', response.data['errors'])

    def test_register_user_password_mismatch(self):
        data = self.user_data.copy()
        data['confirm_password'] = 'differentpassword'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('confirm_password', response.data['errors'])

    def test_change_password_unauthenticated(self):
        data = {
            "old_password": "oldpassword123!",
            "new_password": "newpassword123!",
            "confirm_new_password": "newpassword123!"
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_success(self):
        # Log in first to get JWT token
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access_token = login_response.data['access']

        # Add auth header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "old_password": "oldpassword123!",
            "new_password": "newpassword123!",
            "confirm_new_password": "newpassword123!"
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify we can log in with the new password
        self.client.credentials()  # clear credentials
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "newpassword123!"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_change_password_incorrect_old_password(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "old_password": "wrongoldpassword",
            "new_password": "newpassword123!",
            "confirm_new_password": "newpassword123!"
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('old_password', response.data['errors'])

    def test_change_password_new_password_mismatch(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "old_password": "oldpassword123!",
            "new_password": "newpassword123!",
            "confirm_new_password": "differentnewpassword"
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('confirm_new_password', response.data['errors'])

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_success(self):
        self.user.about_me = "Hello, I am a test user."
        self.user.location_name = "Dhaka, Bangladesh"
        self.user.save()

        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['email'], "existing@example.com")
        self.assertEqual(response.data['profile']['full_name'], "Existing User")
        self.assertEqual(response.data['profile']['about_me'], "Hello, I am a test user.")
        self.assertEqual(response.data['profile']['location_name'], "Dhaka, Bangladesh")

    def test_update_profile_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "full_name": "Updated Name",
            "about_me": "Updated about me description.",
            "location_name": "New York, USA"
        }
        response = self.client.put(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['full_name'], "Updated Name")
        self.assertEqual(response.data['profile']['about_me'], "Updated about me description.")
        self.assertEqual(response.data['profile']['location_name'], "New York, USA")
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated Name")
        self.assertEqual(self.user.about_me, "Updated about me description.")
        self.assertEqual(self.user.location_name, "New York, USA")

    def test_update_profile_photo_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Create a mock image
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = io.BytesIO()
        image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
        image.save(file, 'png')
        file.name = 'test.png'
        file.seek(0)
        
        photo = SimpleUploadedFile(
            "test.png",
            file.read(),
            content_type="image/png"
        )

        data = {
            "full_name": "Updated With Photo",
            "profile_photo": photo
        }
        
        response = self.client.put(self.profile_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsNotNone(response.data['profile']['profile_photo'])
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo.name.startswith('profile_photos/test'))

    def test_patch_profile_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "location_name": "Patched Location Name"
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['location_name'], "Patched Location Name")

        self.user.refresh_from_db()
        self.assertEqual(self.user.location_name, "Patched Location Name")

    def test_update_profile_location_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "latitude": "23.810331",
            "longitude": "90.412518"
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(float(response.data['profile']['latitude']), 23.810331)
        self.assertEqual(float(response.data['profile']['longitude']), 90.412518)

        self.user.refresh_from_db()
        self.assertEqual(float(self.user.latitude), 23.810331)
        self.assertEqual(float(self.user.longitude), 90.412518)

    def test_update_profile_json_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "latitude": "23.780769",
            "longitude": "90.407599"
        }
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(float(response.data['profile']['latitude']), 23.780769)
        self.assertEqual(float(response.data['profile']['longitude']), 90.407599)

    def test_forgot_password_email_not_found(self):
        response = self.client.post(self.forgot_password_url, {"email": "notfound@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_forgot_password_success(self):
        from .models import OTP
        response = self.client.post(self.forgot_password_url, {"email": "existing@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(OTP.objects.filter(email="existing@example.com").exists())

    def test_verify_otp_invalid(self):
        from .models import OTP
        OTP.objects.create(email="existing@example.com", code="1111")
        response = self.client.post(self.verify_otp_url, {"email": "existing@example.com", "otp": "2222"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_verify_otp_success(self):
        from .models import OTP
        otp = OTP.objects.create(email="existing@example.com", code="1111")
        response = self.client.post(self.verify_otp_url, {"email": "existing@example.com", "otp": "1111"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        otp.refresh_from_db()
        self.assertTrue(otp.is_verified)

    def test_reset_password_unverified(self):
        data = {
            "email": "existing@example.com",
            "password": "newresetpassword123!",
            "confirm_password": "newresetpassword123!"
        }
        response = self.client.post(self.reset_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_reset_password_success(self):
        from .models import OTP
        # 1. Request OTP
        self.client.post(self.forgot_password_url, {"email": "existing@example.com"})
        otp_record = OTP.objects.filter(email="existing@example.com").last()
        otp_code = otp_record.code

        # 2. Verify OTP
        verify_response = self.client.post(self.verify_otp_url, {"email": "existing@example.com", "otp": otp_code})
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        # 3. Reset Password
        reset_data = {
            "email": "existing@example.com",
            "password": "newresetpassword123!",
            "confirm_password": "newresetpassword123!"
        }
        reset_response = self.client.post(self.reset_password_url, reset_data)
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertTrue(reset_response.data['success'])

        # OTP should be deleted from DB
        self.assertFalse(OTP.objects.filter(email="existing@example.com").exists())

        # 4. Verify login works with the new password
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "newresetpassword123!"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_update_profile_distance_radius_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "distance_radius": 25
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['distance_radius'], 25)

        self.user.refresh_from_db()
        self.assertEqual(self.user.distance_radius, 25)

    def test_nearby_users_unauthenticated(self):
        url = reverse('nearby_users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nearby_users_missing_coordinates(self):
        # Log in first
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Request user coordinates are None
        self.user.latitude = None
        self.user.longitude = None
        self.user.save()

        url = reverse('nearby_users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('latitude and longitude', response.data['message'])

    def test_nearby_users_success_and_filtering(self):
        # Log in
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Set user location (Dhaka, Bangladesh, roughly 23.780769, 90.4125)
        self.user.latitude = 23.780769
        self.user.longitude = 90.4125
        self.user.distance_radius = 25
        self.user.save()

        # Create user 1 within radius (~1.0 km away)
        user_near = User.objects.create_user(
            username="near@example.com",
            email="near@example.com",
            password="password123!",
            first_name="Near User",
            latitude=23.7898,
            longitude=90.4125
        )

        # Create user 2 far away (~111 km away)
        user_far = User.objects.create_user(
            username="far@example.com",
            email="far@example.com",
            password="password123!",
            first_name="Far User",
            latitude=24.7807,
            longitude=90.4125
        )

        url = reverse('nearby_users')
        
        # 1. Test standard retrieval with profile settings (distance=25)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], user_near.id)
        self.assertEqual(response.data['results'][0]['full_name'], "Near User")
        self.assertIsNotNone(response.data['results'][0]['distance_km'])

        # 2. Test override query parameters (e.g. distance=150 to catch the far user too)
        response_override = self.client.get(f"{url}?distance=150")
        self.assertEqual(response_override.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_override.data['results']), 2)
        # Verify they are sorted by distance ascending (closest first)
        self.assertEqual(response_override.data['results'][0]['id'], user_near.id)
        self.assertEqual(response_override.data['results'][1]['id'], user_far.id)

        # 3. Test override coordinates parameter
        # If we search from coordinates near the far user, we should see the far user first
        response_coord = self.client.get(f"{url}?latitude=24.7807&longitude=90.4125&distance=25")
        self.assertEqual(response_coord.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_coord.data['results']), 1)
        self.assertEqual(response_coord.data['results'][0]['id'], user_far.id)

        # 4. Test search parameter filtering
        # Search for "Near"
        response_search_near = self.client.get(f"{url}?distance=150&search=near")
        self.assertEqual(response_search_near.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_search_near.data['results']), 1)
        self.assertEqual(response_search_near.data['results'][0]['id'], user_near.id)

        # Search for "Far" (case insensitive)
        response_search_far = self.client.get(f"{url}?distance=150&search=fAr")
        self.assertEqual(response_search_far.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_search_far.data['results']), 1)
        self.assertEqual(response_search_far.data['results'][0]['id'], user_far.id)

        # Search for non-existent name
        response_search_none = self.client.get(f"{url}?distance=150&search=nobody")
        self.assertEqual(response_search_none.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_search_none.data['results']), 0)

    def test_friends_flow(self):
        # Create another user to interact with
        user_friend = User.objects.create_user(
            username="friend@example.com",
            email="friend@example.com",
            password="password123!",
            first_name="Friend User"
        )

        # Log in the request user
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # 1. Send friend request
        send_url = reverse('friend_request_send')
        response = self.client.post(send_url, {"receiver_id": user_friend.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['status'], 'pending')

        # Try to send it again (should fail)
        response_dup = self.client.post(send_url, {"receiver_id": user_friend.id})
        self.assertEqual(response_dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response_dup.data['success'])
        self.assertEqual(response_dup.data['message'], "Friend request already sent.")

        # Try to send request to self (should fail)
        response_self = self.client.post(send_url, {"receiver_id": self.user.id})
        self.assertEqual(response_self.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response_self.data['success'])

        # 2. Check pending incoming requests from friend's side
        self.client.credentials()  # log out request user
        friend_login = self.client.post(self.login_url, {
            "email": "friend@example.com",
            "password": "password123!"
        })
        friend_token = friend_login.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {friend_token}')

        requests_url = reverse('friend_requests_incoming')
        response_req = self.client.get(requests_url)
        self.assertEqual(response_req.status_code, status.HTTP_200_OK)
        self.assertEqual(response_req.data['count'], 1)
        self.assertEqual(len(response_req.data['requests']), 1)
        req_id = response_req.data['requests'][0]['id']
        self.assertEqual(response_req.data['requests'][0]['sender']['id'], self.user.id)

        # 3. Reject/Delete request (test rejection first, then we'll send it again and accept it)
        reject_url = reverse('friend_request_reject', args=[req_id])
        response_rej = self.client.post(reject_url)
        self.assertEqual(response_rej.status_code, status.HTTP_200_OK)
        self.assertTrue(response_rej.data['success'])

        # Verify incoming requests is now empty
        response_req = self.client.get(requests_url)
        self.assertEqual(response_req.data['count'], 0)
        self.assertEqual(len(response_req.data['requests']), 0)

        # Send it again from request user's side
        self.client.credentials()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        self.client.post(send_url, {"receiver_id": user_friend.id})

        # Switch back to friend's side to accept it
        self.client.credentials()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {friend_token}')
        response_req = self.client.get(requests_url)
        req_id = response_req.data['requests'][0]['id']

        accept_url = reverse('friend_request_accept', args=[req_id])
        response_acc = self.client.post(accept_url)
        self.assertEqual(response_acc.status_code, status.HTTP_200_OK)
        self.assertTrue(response_acc.data['success'])

        # 4. Check friends list from friend's side
        friends_url = reverse('friends_list')
        response_friends = self.client.get(friends_url)
        self.assertEqual(response_friends.status_code, status.HTTP_200_OK)
        self.assertEqual(response_friends.data['count'], 1)
        self.assertEqual(len(response_friends.data['friends']), 1)
        self.assertEqual(response_friends.data['friends'][0]['id'], self.user.id)

        # Check friends list from request user's side
        self.client.credentials()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response_friends_u = self.client.get(friends_url)
        self.assertEqual(response_friends_u.status_code, status.HTTP_200_OK)
        self.assertEqual(response_friends_u.data['count'], 1)
        self.assertEqual(len(response_friends_u.data['friends']), 1)
        self.assertEqual(response_friends_u.data['friends'][0]['id'], user_friend.id)

        # 5. Remove Friend (unfriend)
        remove_url = reverse('friend_remove', args=[user_friend.id])
        response_rem = self.client.delete(remove_url)
        self.assertEqual(response_rem.status_code, status.HTTP_200_OK)
        self.assertTrue(response_rem.data['success'])

        # Verify friends list is now empty
        response_friends_u = self.client.get(friends_url)
        self.assertEqual(response_friends_u.data['count'], 0)
        self.assertEqual(len(response_friends_u.data['friends']), 0)


