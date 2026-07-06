import json
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from message.models import Conversation, Message

User = get_user_model()

class MessageAPITests(APITestCase):

    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="password123!",
            first_name="Alice"
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="password123!",
            first_name="Bob"
        )
        self.user3 = User.objects.create_user(
            username="user3@example.com",
            email="user3@example.com",
            password="password123!",
            first_name="Charlie"
        )

        # Get JWT tokens
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)

        self.list_create_url = reverse('conversation-list')

    def test_create_and_list_conversations(self):
        # Start conversation Alice -> Bob
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        data = {"receiver_id": self.user2.id}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation_id = response.data['id']

        # Start conversation Alice -> Bob again (should return existing conversation)
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], conversation_id)

        # List Alice's conversations
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['other_participant']['email'], self.user2.email)

    def test_search_conversations(self):
        # Create Alice -> Bob conversation
        conv_bob = Conversation.objects.create()
        conv_bob.participants.add(self.user1, self.user2)

        # Create Alice -> Charlie conversation
        conv_charlie = Conversation.objects.create()
        conv_charlie.participants.add(self.user1, self.user3)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')

        # Search for 'Bob'
        response = self.client.get(self.list_create_url, {'search': 'Bob'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['other_participant']['email'], self.user2.email)

        # Search for 'Charlie'
        response = self.client.get(self.list_create_url, {'search': 'Charlie'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['other_participant']['email'], self.user3.email)

    def test_get_messages_and_read_all(self):
        # Create Alice -> Bob conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        # Bob sends message to Alice
        msg = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content="Hi Alice!"
        )

        messages_url = reverse('conversation-messages', args=[conversation.id])
        read_all_url = reverse('conversation-read-all', args=[conversation.id])

        # Alice checks messages
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['content'], "Hi Alice!")

        # The message should be marked as read now
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

        # Unread message again
        msg2 = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content="Are you there?"
        )
        self.assertFalse(msg2.is_read)

        # Alice calls read_all
        response = self.client.post(read_all_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg2.refresh_from_db()
        self.assertTrue(msg2.is_read)
