from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User


class FoodgramAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_user_registration_missing_field(self):
        response = self.client.post(
            reverse("users-list"),
            {
                "email": "user@example.com",
                "username": "user",
                "first_name": "",
                "last_name": "User",
                "password": "userpass",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recipe_without_ingredients(self):
        response = self.client.post(
            reverse("recipes-list"),
            {
                "name": "Пустой рецепт",
                "text": "Нет ингредиентов",
                "cooking_time": 10,
                "image": None,
                "ingredients": [],
                "tags": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subscription_duplicate(self):
        user2 = User.objects.create_user(
            username="author",
            email="author@example.com",
            password="testpass123",
        )
        self.client.post(reverse("users-subscribe", args=[user2.id]))
        response = self.client.post(
            reverse("users-subscribe", args=[user2.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
