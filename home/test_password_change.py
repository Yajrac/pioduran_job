from django.test import TestCase
from django.urls import reverse
from user.models import User


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='password-user', role='applicant', password='Original!234')
        self.client.force_login(self.user)
        self.url = reverse('change-password')

    def test_password_change_keeps_session(self):
        response = self.client.post(self.url, {'old_password': 'Original!234', 'new_password1': 'Updated!5678', 'new_password2': 'Updated!5678'})
        self.assertRedirects(response, reverse('change-password-done'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Updated!5678'))
        self.assertEqual(str(self.user.pk), self.client.session['_auth_user_id'])
        self.assertContains(self.client.get(response.url), 'changed successfully')

    def test_invalid_passwords_leave_account_unchanged(self):
        for old, new, confirm in [('wrong', 'Updated!5678', 'Updated!5678'), ('Original!234', 'Updated!5678', 'Different!5678'), ('Original!234', 'weak', 'weak')]:
            response = self.client.post(self.url, {'old_password': old, 'new_password1': new, 'new_password2': confirm})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password('Original!234'))

    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), reverse('login-user') + '?next=' + self.url)

    def test_employer_page(self):
        self.user.role = 'employer'
        self.user.save()
        self.assertTemplateUsed(self.client.get(self.url), 'employer_base.html')
