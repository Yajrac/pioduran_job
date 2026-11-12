from django.test import TestCase, override_settings
from django.urls import reverse

from employer.models import EmployerRegistrationOTP

FORM = {
    'username': 'newcompany', 'email': 'hr@newcompany.example', 'password': 'Strong#2026', 'confirm_password': 'Strong#2026',
    'company_name': 'New Company', 'business_permit_no': 'BP-777', 'contact_no': '09171234567', 'description': 'd',
}


class DemoSmsTests(TestCase):
    @override_settings(DEBUG=True, OTP_DEV_MODE=True)
    def test_demo_mode_shows_the_code_on_the_verify_page(self):
        self.client.post(reverse('employee-registration'), FORM)
        code = EmployerRegistrationOTP.objects.get(username='newcompany').otp_code
        response = self.client.get(reverse('verify-employer-registration'))
        self.assertContains(response, 'DEMO MODE')
        self.assertContains(response, f'data-demo-code="{code}"')
        self.assertContains(response, '0917•••4567')

    @override_settings(DEBUG=False, OTP_DEV_MODE=True, SMS_PROVIDER='semaphore', SEMAPHORE_API_KEY='')
    def test_code_is_never_shown_outside_demo_mode(self):
        session = self.client.session
        session['demo_sms'] = {'to': 'x', 'message': 'leak', 'code': '123456'}
        session['employer_registration_id'] = EmployerRegistrationOTP.objects.create(
            username='u', email='e@x.com', password='x', company_name='c', business_permit_no='b',
            contact_no='09170000000', otp_code='123456',
            expires_at='2999-01-01T00:00:00Z').pk
        session.save()
        response = self.client.get(reverse('verify-employer-registration'))
        self.assertNotContains(response, 'DEMO MODE')
        self.assertNotContains(response, '123456')
