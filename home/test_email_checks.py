from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from home import email_checks
from home.email_checks import email_domain_error, suggest_email
from home.registration_validation import employer_field_errors


class SuggestEmailTests(TestCase):
    def test_typos_of_popular_domains_get_a_suggestion(self):
        for typed, expected in [('1233@gmaiil.com', '1233@gmail.com'), ('a@gmial.com', 'a@gmail.com'),
                                ('a@gmail.con', 'a@gmail.com'), ('a@yahooo.com', 'a@yahoo.com'),
                                ('a@hotmial.com', 'a@hotmail.com')]:
            self.assertEqual(suggest_email(typed), expected)

    def test_correct_or_unrelated_domains_are_left_alone(self):
        for typed in ['a@gmail.com', 'a@mail.com', 'a@deped.gov.ph', 'a@company.com.ph', 'not-an-email']:
            self.assertIsNone(suggest_email(typed))


@override_settings(EMAIL_DOMAIN_CHECK=True)
class DomainCheckTests(TestCase):
    def setUp(self):
        email_checks.domain_accepts_mail.cache_clear()

    def fake_dns(self, existing):
        return patch.object(email_checks, 'domain_accepts_mail', side_effect=lambda d: d in existing)

    def test_unknown_domain_is_rejected(self):
        with self.fake_dns({'gmail.com'}):
            self.assertIn('does not exist', email_domain_error('123@hagvd.gov'))
            self.assertEqual(email_domain_error('maria@gmail.com'), '')

    @override_settings(EMAIL_DOMAIN_CHECK=False)
    def test_can_be_turned_off(self):
        self.assertEqual(email_domain_error('123@hagvd.gov'), '')

    def test_check_endpoint_reports_domain_and_suggestion(self):
        with self.fake_dns({'gmail.com', 'gmaiil.com'}):
            data = self.client.get(reverse('check-registration-email'), {'email': '1233@gmaiil.com'}).json()
            self.assertTrue(data['available'])
            self.assertEqual(data['suggestion'], '1233@gmail.com')
            data = self.client.get(reverse('check-registration-email'), {'email': '123@hagvd.gov'}).json()
            self.assertFalse(data['available'])
            self.assertIn('does not exist', data['error'])

    def test_employer_registration_rejects_unknown_domain(self):
        with self.fake_dns(set()):
            errors = employer_field_errors({'email': 'hr@hagvd.gov'})
        self.assertIn('does not exist', errors['email'])

    def test_applicant_registration_rejects_unknown_domain(self):
        with self.fake_dns(set()):
            response = self.client.post(reverse('applicant-registration'), {
                'username': 'newperson', 'email': 'me@hagvd.gov', 'password': 'Strong#2026',
                'confirm_password': 'Strong#2026', 'first_name': 'Ana', 'last_name': 'Cruz',
                'phone_number': '09171234567', 'skills': 'Sales'})
        self.assertContains(response, 'does not exist')

    def test_dns_outage_does_not_block(self):
        import dns.exception
        email_checks.domain_accepts_mail.cache_clear()
        with patch('dns.resolver.Resolver.resolve', side_effect=dns.exception.Timeout):
            self.assertEqual(email_domain_error('maria@somewhere-new.ph'), '')

    def test_dns_outage_is_not_remembered(self):
        import dns.exception
        email_checks.domain_accepts_mail.cache_clear()
        with patch('dns.resolver.Resolver.resolve', side_effect=dns.exception.Timeout):
            self.assertEqual(email_domain_error('me@nowhere-xyz.com'), '')
        with patch('dns.resolver.Resolver.resolve', side_effect=dns.resolver.NXDOMAIN):
            self.assertIn('does not exist', email_domain_error('me@nowhere-xyz.com'))
