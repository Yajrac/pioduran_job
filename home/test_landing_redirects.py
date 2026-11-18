from django.test import TestCase
from django.urls import reverse

from employer.models import Employer
from user.models import User

LANDING = ['home', 'login-user', 'peso-login', 'applicant-registration', 'employee-registration', 'forgot-password']


class SignedInLandingRedirectTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('pesoadmin', 'a@example.com', 'x', role='admin')
        self.employer = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        Employer.objects.create(employer=self.employer, company_name='Store', business_permit_no='BP-1',
                                contact_no='09170000001', description='d', approval_status='approved')
        self.applicant = User.objects.create_user('maria', 'm@example.com', 'x', role='applicant')

    def assert_landing_goes_to(self, user, target):
        self.client.force_login(user)
        for name in LANDING:
            with self.subTest(user=user.username, page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], reverse(target))

    def test_admin_goes_to_admin_dashboard(self):
        self.assert_landing_goes_to(self.admin, 'peso-dashboard')

    def test_employer_goes_to_employer_overview(self):
        self.assert_landing_goes_to(self.employer, 'employer-dashboard')

    def test_applicant_goes_to_my_profile(self):
        self.assert_landing_goes_to(self.applicant, 'applicant-profile')

    def test_public_pages_stay_open_when_signed_in(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('browse-job')).status_code, 200)

    def test_signed_out_visitors_still_see_home(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('login-user')).status_code, 200)
