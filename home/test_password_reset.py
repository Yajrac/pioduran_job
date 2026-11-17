import re
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer
from home.models import PasswordResetCode
from home.password_reset import normalize_phone
from home.sms import SMSResult
from user.models import User

OK = SMSResult(True, 'test')


def code_from(send):
    """The 6-digit code from the most recent reset SMS."""
    for call in reversed(send.call_args_list):
        found = re.search(r'reset code is (\d{6})', call.args[1])
        if found:
            return found.group(1)
    raise AssertionError('no reset code was sent')


@override_settings(DEBUG=False, OTP_DEV_MODE=False)
@patch('home.password_reset.send_sms', return_value=OK)
class PasswordResetTests(TestCase):
    def setUp(self):
        self.maria = User.objects.create_user('maria', 'maria@example.com', 'Old#Pass2026', role='applicant')
        Applicant.objects.create(user=self.maria, first_name='Maria', last_name='Cruz', middle_name='',
                                 email='maria@example.com', phone_number='09171234567')

    def start(self, identifier):
        return self.client.post(reverse('forgot-password'), {'identifier': identifier})

    def finish(self, send, password='New#Pass2026'):
        self.client.post(reverse('forgot-password-verify'), {'otp': code_from(send)})
        return self.client.post(reverse('forgot-password-new'), {'new_password1': password, 'new_password2': password})

    def test_login_page_links_to_forgot_password(self, send):
        self.assertContains(self.client.get(reverse('login-user')), reverse('forgot-password'))

    def test_full_reset_by_number_in_any_format(self, send):
        for identifier in ['09171234567', '+63 917 123 4567', '0917-123-4567']:
            with self.subTest(identifier=identifier):
                self.start(identifier)
                self.assertEqual(send.call_args.args[0], '09171234567')
                response = self.finish(send, password=f'New#Pass{len(identifier)}x')
                self.assertRedirects(response, reverse('login-user'))
                self.maria.refresh_from_db()
                self.assertTrue(self.maria.check_password(f'New#Pass{len(identifier)}x'))
                PasswordResetCode.objects.all().delete()  # stay under the hourly limit
        self.assertIn('Your password was changed', send.call_args.args[1])

    def test_unknown_account_shows_the_same_message_and_sends_nothing(self, send):
        known = self.start('09171234567')
        send.reset_mock()
        unknown = self.client.post(reverse('forgot-password'), {'identifier': '09990000000'}, follow=True)
        self.assertRedirects(known, reverse('forgot-password-verify'))
        self.assertContains(unknown, 'If an account matches')
        send.assert_not_called()

    def test_code_is_hashed_and_wrong_codes_are_limited(self, send):
        self.start('09171234567')
        record = PasswordResetCode.objects.get()
        self.assertNotIn(code_from(send), record.code_hash)
        for _ in range(5):
            self.client.post(reverse('forgot-password-verify'), {'otp': '000000'})
        response = self.client.post(reverse('forgot-password-verify'), {'otp': code_from(send)})
        self.assertContains(response, 'Too many wrong attempts')
        self.assertEqual(self.client.get(reverse('forgot-password-new')).status_code, 302)

    def test_expired_code_is_rejected(self, send):
        self.start('09171234567')
        PasswordResetCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.post(reverse('forgot-password-verify'), {'otp': code_from(send)})
        self.assertContains(response, 'expired')

    def test_at_most_three_codes_per_hour(self, send):
        for _ in range(4):
            self.start('09171234567')
        self.assertEqual(send.call_count, 3)

    def test_new_password_page_needs_a_verified_code(self, send):
        self.assertRedirects(self.client.get(reverse('forgot-password-new')), reverse('forgot-password'))
        self.start('09171234567')
        self.assertRedirects(self.client.get(reverse('forgot-password-new')), reverse('forgot-password'))

    def test_only_a_mobile_number_is_accepted(self, send):
        for identifier in ['maria', 'maria@example.com', '12345']:
            with self.subTest(identifier=identifier):
                response = self.start(identifier)
                self.assertContains(response, 'Enter an 11-digit mobile number starting with 09.')
        send.assert_not_called()

    def test_admin_accounts_cannot_be_reset(self, send):
        self.maria.role = 'admin'
        self.maria.save()
        self.start('09171234567')
        send.assert_not_called()

    def test_one_number_with_applicant_and_employer_asks_which_account(self, send):
        owner = User.objects.create_user('rawisstore', 'store@example.com', 'x', role='employer')
        Employer.objects.create(employer=owner, company_name='Rawis Store', business_permit_no='BP-1',
                                contact_no='09171234567', description='d')
        self.start('09171234567')
        response = self.client.post(reverse('forgot-password-verify'), {'otp': code_from(send)})
        self.assertRedirects(response, reverse('forgot-password-account'))
        page = self.client.get(reverse('forgot-password-account'))
        self.assertContains(page, 'rawisstore')
        self.assertContains(page, 'Employer · Rawis Store')
        self.client.post(reverse('forgot-password-account'), {'account': owner.pk})
        self.client.post(reverse('forgot-password-new'), {'new_password1': 'Store#Pass2026', 'new_password2': 'Store#Pass2026'})
        owner.refresh_from_db()
        self.assertTrue(owner.check_password('Store#Pass2026'))

    def test_reset_signs_out_other_sessions(self, send):
        other_device = self.client_class()
        other_device.force_login(self.maria)
        self.start('09171234567')
        self.finish(send)
        self.assertEqual(other_device.get(reverse('applicant-profile')).status_code, 302)


class PhoneFormatTests(TestCase):
    def test_normalize_phone(self):
        for value in ['09171234567', '+639171234567', '639171234567', '0917 123 4567', '9171234567']:
            self.assertEqual(normalize_phone(value), '09171234567')
        self.assertEqual(normalize_phone('maria'), '')


class EditProfilePhoneTests(TestCase):
    def test_cannot_take_another_applicants_number(self):
        for name, phone in [('ana', '09170000001'), ('ben', '09170000002')]:
            user = User.objects.create_user(name, f'{name}@example.com', 'x', role='applicant')
            Applicant.objects.create(user=user, first_name=name, last_name='X', middle_name='',
                                     email=f'{name}@example.com', phone_number=phone)
        self.client.force_login(User.objects.get(username='ben'))
        response = self.client.post(reverse('edit-applicant-profile'), {
            'first_name': 'ben', 'last_name': 'X', 'email': 'ben@example.com', 'phone_number': '09170000001'})
        self.assertContains(response, 'already used by another account')
        self.assertEqual(Applicant.objects.get(user__username='ben').phone_number, '09170000002')
