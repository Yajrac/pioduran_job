from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LoginAttemptWindow


class LoginLimitTests(TestCase):
    def attempt(self, username='limit-test'):
        return self.client.post(reverse('login-user'), {
            'username': username, 'password': 'incorrect',
        }, HTTP_ACCEPT='application/json')

    @patch('home.views.authenticate', return_value=None)
    def test_limit_blocks_authentication_and_survives_new_session(self, auth):
        for _ in range(4):
            self.assertEqual(self.attempt().status_code, 400)
        fifth = self.attempt()
        self.assertEqual(fifth.status_code, 429)
        self.assertGreater(int(fifth['Retry-After']), 0)
        self.client.cookies.clear()
        self.assertEqual(self.attempt('LIMIT-TEST').status_code, 429)
        self.assertEqual(auth.call_count, 5)

    @patch('home.views.authenticate', return_value=None)
    def test_warns_on_third_and_fourth_failure(self, auth):
        for count in range(1, 5):
            response = self.attempt()
            if count < 3:
                self.assertNotIn('warning', response.json())
            else:
                self.assertIn(f'{count} failed login attempts', response.json()['warning'])
                self.assertIn(f'{5-count} attempt(s) remaining', response.json()['warning'])

    @patch('home.views.authenticate', return_value=None)
    def test_cooldown_expires(self, auth):
        for _ in range(5):
            self.attempt()
        LoginAttemptWindow.objects.update(locked_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.attempt().status_code, 400)
        self.assertEqual(LoginAttemptWindow.objects.get().attempts, 1)

    @patch('home.views.login')
    @patch('home.views.authenticate')
    def test_success_resets_counter(self, auth, login):
        auth.return_value = None
        self.attempt()
        auth.return_value = SimpleNamespace(role='applicant')
        response = self.attempt()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect'], reverse('applicant-profile'))
        self.assertFalse(LoginAttemptWindow.objects.exists())
