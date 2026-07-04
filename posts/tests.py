from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Post

User = get_user_model()

class PostTests(APITestCase):

    def setUp(self):
        # Create User 1
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            first_name="User One"
        )
        # Create User 2
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            first_name="User Two"
        )

        self.login_url = reverse('login')
        self.posts_url = reverse('post-list')
        self.my_posts_url = reverse('post-my-posts')

        # Log in User 1
        login_response = self.client.post(self.login_url, {
            "email": "user1@example.com",
            "password": "password123!"
        })
        self.access_token1 = login_response.data['access']
        
        # Log in User 2
        login_response = self.client.post(self.login_url, {
            "email": "user2@example.com",
            "password": "password123!"
        })
        self.access_token2 = login_response.data['access']

        # Default client is authenticated as User 1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')

    def test_create_post_success(self):
        data = {
            "content": "This is a new test post!"
        }
        response = self.client.post(self.posts_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], "This is a new test post!")
        self.assertEqual(response.data['creator']['email'], "user1@example.com")

        # Verify created in DB
        self.assertEqual(Post.objects.filter(creator=self.user1).count(), 1)

    def test_edit_own_post_success(self):
        # Create post
        post = Post.objects.create(creator=self.user1, content="Original content")
        detail_url = reverse('post-detail', kwargs={'pk': post.id})

        # Update (PUT)
        data = {"content": "Updated content via PUT"}
        response = self.client.put(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], "Updated content via PUT")

        # Update (PATCH)
        data = {"content": "Updated content via PATCH"}
        response = self.client.patch(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], "Updated content via PATCH")

    def test_edit_other_user_post_forbidden(self):
        # Create post by User 2
        post = Post.objects.create(creator=self.user2, content="User 2 post")
        detail_url = reverse('post-detail', kwargs={'pk': post.id})

        # Try to update as User 1
        data = {"content": "Malicious edit"}
        response = self.client.put(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify not changed in DB
        post.refresh_from_db()
        self.assertEqual(post.content, "User 2 post")

    def test_delete_post_success(self):
        post = Post.objects.create(creator=self.user1, content="To be deleted")
        detail_url = reverse('post-detail', kwargs={'pk': post.id})

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.filter(id=post.id).count(), 0)

    def test_delete_other_user_post_forbidden(self):
        post = Post.objects.create(creator=self.user2, content="User 2 post")
        detail_url = reverse('post-detail', kwargs={'pk': post.id})

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Post.objects.filter(id=post.id).count(), 1)

    def test_list_posts_filtering(self):
        # Create posts for both users
        Post.objects.create(creator=self.user1, content="User 1 post")
        Post.objects.create(creator=self.user2, content="User 2 post")

        # 1. Default list gets all posts
        response = self.client.get(self.posts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # 2. Filter by user_id
        response = self.client.get(self.posts_url, {"user_id": self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['creator']['email'], "user2@example.com")

        # 3. Get my-posts
        response = self.client.get(self.my_posts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['creator']['email'], "user1@example.com")

    def test_like_post_toggle_success(self):
        post = Post.objects.create(creator=self.user2, content="User 2 post")
        like_url = reverse('post-like', kwargs={'pk': post.id})

        # 1. Like the post (first toggle)
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['liked'])
        self.assertEqual(response.data['likes_count'], 1)

        # Verify in DB
        self.assertEqual(post.likes.filter(user=self.user1).count(), 1)

        # 2. Unlike the post (second toggle)
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['liked'])
        self.assertEqual(response.data['likes_count'], 0)

        # Verify in DB
        self.assertEqual(post.likes.filter(user=self.user1).count(), 0)

    def test_comment_post_success(self):
        post = Post.objects.create(creator=self.user2, content="User 2 post")
        comment_url = reverse('post-comment', kwargs={'pk': post.id})

        data = {"content": "This is a comment!"}
        response = self.client.post(comment_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], "This is a comment!")
        self.assertEqual(response.data['user']['email'], "user1@example.com")

        # Verify in DB
        self.assertEqual(post.comments.filter(user=self.user1).count(), 1)

    def test_comment_post_missing_content(self):
        post = Post.objects.create(creator=self.user2, content="User 2 post")
        comment_url = reverse('post-comment', kwargs={'pk': post.id})

        # Test with empty/missing content
        response = self.client.post(comment_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upcoming_endpoint_includes_likes_and_comments(self):
        from accounts.models import Friendship
        # Establish friendship so User 2's posts show up in User 1's upcoming feed
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status='accepted')

        post = Post.objects.create(creator=self.user2, content="Friend post")
        
        # Add a like from User 1
        post.likes.create(user=self.user1)

        # Add a comment from User 1
        comment = post.comments.create(user=self.user1, content="Looks great!")

        # Make sure user1 location is set so they can access the upcoming API
        self.user1.latitude = 40.7128
        self.user1.longitude = -74.0060
        self.user1.save()

        upcoming_url = reverse('event-upcoming')
        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find the post in the returned items
        post_items = [item for item in response.data if item.get('type') == 'post']
        self.assertEqual(len(post_items), 1)
        
        post_item = post_items[0]
        self.assertEqual(post_item['id'], post.id)
        self.assertEqual(post_item['likes_count'], 1)
        self.assertTrue(post_item['has_liked'])
        self.assertEqual(len(post_item['comments']), 1)
        self.assertEqual(post_item['comments'][0]['content'], "Looks great!")
        self.assertEqual(post_item['comments'][0]['user']['email'], "user1@example.com")

