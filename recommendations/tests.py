import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Recommendation, RecommendationPhoto

User = get_user_model()

class RecommendationAPITests(APITestCase):

    def setUp(self):
        self.list_create_url = reverse('recommendation-list')

        # Create two test users
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            first_name="User One"
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            first_name="User Two"
        )

        # Get JWT tokens for authentication
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)

        # Helper method for mock images
        self.mock_photos = []
        for i in range(2):
            file = io.BytesIO()
            image = Image.new('RGBA', size=(100, 100), color=(100 + i * 20, 100, 100))
            image.save(file, 'png')
            file.name = f'test_image_{i}.png'
            file.seek(0)
            uploaded_file = SimpleUploadedFile(
                f"test_image_{i}.png",
                file.read(),
                content_type="image/png"
            )
            self.mock_photos.append(uploaded_file)

    def test_unauthorized_endpoints(self):
        # 1. List
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create a sample recommendation manually to test details, update, delete
        rec = Recommendation.objects.create(
            creator=self.user1,
            category="Services",
            details="Great plumber",
            latitude=23.780769,
            longitude=90.407599
        )
        detail_url = reverse('recommendation-detail', args=[rec.id])

        # 2. Retrieve detail
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Create
        response = self.client.post(self.list_create_url, {"details": "Unauthorized Rec"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. Update
        response = self.client.patch(detail_url, {"details": "Unauthorized Update"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 5. Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_recommendation_success_json(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "category": "Services (Plumbing)",
            "details": "Need a reliable plumber in Richmond ASAP.",
            "latitude": "23.7807692141219000",
            "longitude": "90.4075994222697300",
            "location_name": "Plumber Office, Richmond"
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], "Services (Plumbing)")
        self.assertEqual(response.data['creator']['email'], self.user1.email)
        self.assertEqual(float(response.data['latitude']), 23.7807692141219)
        self.assertEqual(float(response.data['longitude']), 90.40759942226973)
        self.assertEqual(response.data['location_name'], "Plumber Office, Richmond")

    def test_create_recommendation_success_multipart_multiple_photos(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {
            "category": "Food (Cafes)",
            "rating": 5,
            "business_name": "Richmond Espresso",
            "details": "Best sourdough toast in town!",
            "latitude": "23.7800000000000000",
            "longitude": "90.4000000000000000",
            "photos": self.mock_photos  # list of 2 image files
        }
        response = self.client.post(self.list_create_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], "Food (Cafes)")
        self.assertEqual(len(response.data['photos']), 2)
        
        rec = Recommendation.objects.get(id=response.data['id'])
        self.assertEqual(rec.photos.count(), 2)

    def test_list_and_retrieve_recommendations(self):
        # Set User 1 coordinates
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.save()

        # Create recs under different users
        rec1 = Recommendation.objects.create(
            creator=self.user1,
            category="Cat 1",
            details="Details 1"
        )
        rec2 = Recommendation.objects.create(
            creator=self.user2,
            category="Cat 2",
            details="Details 2",
            latitude=23.790000,
            longitude=90.410000
        )

        # Retrieve list as User 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Retrieve detail of User 2's rec as User 1
        detail_url = reverse('recommendation-detail', args=[rec2.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['details'], "Details 2")
        self.assertEqual(response.data['creator']['email'], self.user2.email)
        self.assertEqual(response.data['type'], "recommendation")
        self.assertIsNotNone(response.data['distance_km'])
        self.assertLess(response.data['distance_km'], 2.0)


    def test_update_recommendation_permissions_and_photo_replacement(self):
        # Create a recommendation with initial photo
        rec = Recommendation.objects.create(
            creator=self.user1,
            category="Initial Cat",
            details="Initial Details"
        )
        # Create a photo manually
        RecommendationPhoto.objects.create(recommendation=rec, image=self.mock_photos[0])
        self.assertEqual(rec.photos.count(), 1)

        detail_url = reverse('recommendation-detail', args=[rec.id])

        # Try updating as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.patch(detail_url, {"details": "Hacked Details"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        rec.refresh_from_db()
        self.assertEqual(rec.details, "Initial Details")

        # Update details and photos as User 1 (creator) -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # Prepare a new photo list (using the remaining mock photo)
        new_photos = [self.mock_photos[1]]
        data = {
            "details": "Updated Details",
            "location_name": "Updated Location",
            "photos": new_photos
        }
        
        response = self.client.patch(detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rec.refresh_from_db()
        self.assertEqual(rec.details, "Updated Details")
        self.assertEqual(rec.location_name, "Updated Location")
        # Existing photos should have been replaced with the new photo
        self.assertEqual(rec.photos.count(), 1)
        self.assertTrue(rec.photos.first().image.name.startswith('recommendation_photos/test_image_1'))

    def test_delete_recommendation_permissions(self):
        rec = Recommendation.objects.create(
            creator=self.user1,
            category="Cat",
            details="Details"
        )
        detail_url = reverse('recommendation-detail', args=[rec.id])

        # Try deleting as User 2 (not creator) -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Recommendation.objects.filter(id=rec.id).exists())

        # Delete as User 1 (creator) -> 204 No Content
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recommendation.objects.filter(id=rec.id).exists())

    def test_likes_comments_shares(self):
        rec = Recommendation.objects.create(
            creator=self.user2,
            category="Dining",
            details="Great food"
        )
        like_url = reverse('recommendation-like', args=[rec.id])
        comment_url = reverse('recommendation-comment', args=[rec.id])
        share_url = reverse('recommendation-share', args=[rec.id])

        # Test Liking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['liked'])
        self.assertEqual(response.data['likes_count'], 1)

        # Retrieve detail to see if likes updated
        detail_url = reverse('recommendation-detail', args=[rec.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.data['likes_count'], 1)
        self.assertTrue(response.data['has_liked'])
        self.assertFalse(response.data['has_shared'])

        # Test Unliking
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['liked'])
        self.assertEqual(response.data['likes_count'], 0)

        # Like again to test persistence
        self.client.post(like_url)

        # Test Commenting
        # Empty comment should fail
        response = self.client.post(comment_url, {"content": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Good comment
        response = self.client.post(comment_url, {"content": "This is a comment"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], "This is a comment")
        self.assertEqual(response.data['user']['email'], self.user1.email)

        # Verify comment on recommendation detail
        response = self.client.get(detail_url)
        self.assertEqual(response.data['comments_count'], 1)
        self.assertEqual(len(response.data['comments']), 1)
        self.assertEqual(response.data['comments'][0]['content'], "This is a comment")

        # Test Sharing
        response = self.client.post(share_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['shared'])
        self.assertEqual(response.data['shares_count'], 1)

        # Verify shares updated on detail
        response = self.client.get(detail_url)
        self.assertEqual(response.data['shares_count'], 1)
        self.assertTrue(response.data['has_shared'])

        # Verify through Upcoming API
        # To fetch in upcoming API, user1 and user2 need location coordinates and to be within radius (or friends)
        # Let's make user1 and user2 friends
        from accounts.models import Friendship
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status='accepted')

        # Let's set user1 coordinates so upcoming doesn't error out
        self.user1.latitude = 23.780769
        self.user1.longitude = 90.407599
        self.user1.save()

        upcoming_url = reverse('event-upcoming')
        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find our recommendation in the list
        rec_in_upcoming = None
        for item in response.data:
            if item.get('type') == 'recommendation' and item.get('id') == rec.id:
                rec_in_upcoming = item
                break
        
        self.assertIsNotNone(rec_in_upcoming)
        self.assertEqual(rec_in_upcoming['likes_count'], 1)
        self.assertTrue(rec_in_upcoming['has_liked'])
        self.assertEqual(rec_in_upcoming['comments_count'], 1)
        self.assertEqual(len(rec_in_upcoming['comments']), 1)
        self.assertEqual(rec_in_upcoming['comments'][0]['content'], "This is a comment")
        self.assertEqual(rec_in_upcoming['shares_count'], 1)
        self.assertTrue(rec_in_upcoming['has_shared'])

