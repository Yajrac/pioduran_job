from types import SimpleNamespace
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from home.models import LoginAttemptWindow


class AdminLoginTests(TestCase):
    def attempt(self):
        return self.client.post(reverse('peso-login'), {'username': 'admin-test', 'password': 'wrong'}, HTTP_ACCEPT='application/json')

    @patch('core.views.authenticate', return_value=None)
    def test_limit_and_warnings(self, auth):
        for count in range(1, 6):
            response = self.attempt()
            if count in [3,4]:
                self.assertIn('warning', response.json())
        self.assertEqual(response.status_code, 429)
        self.assertGreater(response.json()['retry_after'], 0)
        self.assertEqual(self.attempt().status_code, 429)
        self.assertEqual(auth.call_count, 5)

    @patch('core.views.login')
    @patch('core.views.authenticate', return_value=SimpleNamespace(role='admin', is_authenticated=True, is_superuser=False))
    def test_success_redirect(self, auth, login):
        response = self.attempt()
        self.assertEqual(response.json()['redirect'], reverse('peso-dashboard'))
        self.assertFalse(LoginAttemptWindow.objects.exists())

    @patch('core.views.login')
    @patch('core.views.authenticate', return_value=SimpleNamespace(role='applicant', is_authenticated=True, is_superuser=False))
    def test_other_role_not_logged_in(self, auth, login):
        response = self.attempt()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['clear_fields'], ['username','password'])
        login.assert_not_called()
