from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import CustomUser


class UserAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse("user-register")
        self.login_url = reverse("token_obtain_pair")
        self.profile_url = reverse("user-profile")
        self.leaderboard_url = reverse("user-leaderboard")
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferred_subject": "Math",
        }
        self.user = CustomUser.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="existingpass123",
            rating=1500,
        )

    def test_registration(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomUser.objects.filter(username="testuser").exists())

    def test_login_success(self):
        CustomUser.objects.create_user(username="loginuser", password="loginpass123")
        response = self.client.post(
            self.login_url, {"username": "loginuser", "password": "loginpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_failure(self):
        response = self.client.post(
            self.login_url, {"username": "nouser", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_retrieve(self):
        user = CustomUser.objects.create_user(
            username="profileuser", password="profilepass123"
        )
        login = self.client.post(
            self.login_url, {"username": "profileuser", "password": "profilepass123"}
        )
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "profileuser")

    def test_leaderboard(self):
        CustomUser.objects.create_user(
            username="topuser", password="topuserpass", rating=2000
        )
        response = self.client.get(self.leaderboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u["username"] for u in response.data]
        self.assertIn("topuser", usernames)
        self.assertIn("existinguser", usernames)
