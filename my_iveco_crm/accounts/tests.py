from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from users.models import UserProfile

LOGIN_URL = '/api/token/'


class JWTLoginResponseTest(TestCase):
    """Tests for MyTokenObtainPairView — custom JWT login response."""

    def setUp(self):
        self.client = APIClient()

    def _login(self, username, password):
        return self.client.post(LOGIN_URL, {'username': username, 'password': password})

    def _make_user(self, username, password='pass123', role=None, **kwargs):
        user = User.objects.create_user(username=username, password=password, **kwargs)
        if role is not None:
            # UserProfile is auto-created via post_save signal — update it
            UserProfile.objects.update_or_create(user=user, defaults={'role': role})
        return user

    # ── Response structure ──────────────────────────────────────────────────

    def test_successful_login_returns_200(self):
        self._make_user('mechanic1', role='mechanic')
        response = self._login('mechanic1', 'pass123')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_contains_access_and_refresh_tokens(self):
        self._make_user('mechanic1', role='mechanic')
        data = self._login('mechanic1', 'pass123').json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    def test_response_contains_user_object(self):
        self._make_user('mechanic1', password='pass123', role='mechanic',
                        first_name='Іван', last_name='Коваль', email='ivan@example.com')
        data = self._login('mechanic1', 'pass123').json()
        user = data.get('user', {})
        self.assertEqual(user['username'], 'mechanic1')
        self.assertEqual(user['first_name'], 'Іван')
        self.assertEqual(user['last_name'], 'Коваль')
        self.assertEqual(user['email'], 'ivan@example.com')
        self.assertIn('id', user)

    def test_wrong_credentials_returns_401(self):
        self._make_user('mechanic1', role='mechanic')
        response = self._login('mechanic1', 'wrongpassword')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Role logic ──────────────────────────────────────────────────────────

    def test_user_with_admin_profile_returns_admin_role(self):
        self._make_user('admin1', role='admin')
        data = self._login('admin1', 'pass123').json()
        self.assertEqual(data['user']['role'], 'admin')

    def test_user_with_manager_profile_returns_manager_role(self):
        self._make_user('manager1', role='manager')
        data = self._login('manager1', 'pass123').json()
        self.assertEqual(data['user']['role'], 'manager')

    def test_user_with_mechanic_profile_returns_mechanic_role(self):
        self._make_user('mechanic1', role='mechanic')
        data = self._login('mechanic1', 'pass123').json()
        self.assertEqual(data['user']['role'], 'mechanic')

    def test_superuser_with_admin_profile_returns_admin_role(self):
        # UserProfile is always auto-created via signal, so the is_superuser
        # fallback in the serializer is unreachable in practice.
        # Superusers get role='admin' by explicitly setting it on the profile.
        self._make_user('superadmin', is_superuser=True, is_staff=True, role='admin')
        data = self._login('superadmin', 'pass123').json()
        self.assertEqual(data['user']['role'], 'admin')

    def test_regular_user_without_profile_returns_mechanic_role(self):
        User.objects.create_user(username='noprofile', password='pass123')
        data = self._login('noprofile', 'pass123').json()
        self.assertEqual(data['user']['role'], 'mechanic')
