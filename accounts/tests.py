from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AccountsAPITests(APITestCase):

    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('token_obtain_pair')
        self.change_password_url = reverse('change_password')

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
            "username": "existing@example.com",
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
            "username": "existing@example.com",
            "password": "newpassword123!"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_change_password_incorrect_old_password(self):
        login_response = self.client.post(self.login_url, {
            "username": "existing@example.com",
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
            "username": "existing@example.com",
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

