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

    def test_update_profile_success(self):
        login_response = self.client.post(self.login_url, {
            "email": "existing@example.com",
            "password": "oldpassword123!"
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        data = {
            "full_name": "Updated Name"
        }
        response = self.client.put(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['full_name'], "Updated Name")
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated Name")

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
            "full_name": "Patched Name"
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['full_name'], "Patched Name")

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Patched Name")

