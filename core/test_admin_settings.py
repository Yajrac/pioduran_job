from django.test import TestCase
from django.urls import reverse

from user.models import User


class AdminSettingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('pesoadmin', email='old@example.com', password='OldPass#2026', role='admin')
        self.url = reverse('admin-settings')
        self.client.force_login(self.admin)

    def test_only_admins_can_open_settings(self):
        applicant = User.objects.create_user('person', password='x', role='applicant')
        self.client.force_login(applicant)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_page_shows_both_sections_and_sidebar_link(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Account details')
        self.assertContains(response, 'Change password')
        self.assertEqual(response.context['admin_nav_section'], 'settings')

    def test_update_profile(self):
        response = self.client.post(self.url, {'form': 'profile', 'first_name': 'Ana', 'last_name': 'Reyes', 'email': 'ana@example.com'}, follow=True)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.get_full_name(), self.admin.email), ('Ana Reyes', 'ana@example.com'))
        self.assertContains(response, 'Account details updated.')

    def test_email_must_be_unique(self):
        User.objects.create_user('other', email='taken@example.com', password='x')
        response = self.client.post(self.url, {'form': 'profile', 'first_name': 'A', 'last_name': 'B', 'email': 'taken@example.com'})
        self.assertContains(response, 'already used by another account')

    def test_change_password_keeps_admin_signed_in(self):
        response = self.client.post(self.url, {'form': 'password', 'old_password': 'OldPass#2026',
                                               'new_password1': 'NewPass#2027', 'new_password2': 'NewPass#2027'}, follow=True)
        self.assertContains(response, 'Password changed successfully.')
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('NewPass#2027'))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_wrong_current_or_weak_password_is_rejected(self):
        self.client.post(self.url, {'form': 'password', 'old_password': 'wrong',
                                    'new_password1': 'NewPass#2027', 'new_password2': 'NewPass#2027'})
        response = self.client.post(self.url, {'form': 'password', 'old_password': 'OldPass#2026',
                                               'new_password1': 'weakpass', 'new_password2': 'weakpass'})
        self.assertContains(response, 'uppercase')
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('OldPass#2026'))
