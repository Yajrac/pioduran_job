from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .permit_test_utils import TempPermitStorageMixin, registration_form
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from home.sms import SMSResult, SMS_BRAND
from user.models import User



@override_settings(DEBUG=False, OTP_DEV_MODE=False)
class SmsBrandingTests(TempPermitStorageMixin, TestCase):
    @patch('home.views.send_sms', return_value=SMSResult(True, 'test'))
    def test_employer_otp_names_the_portal(self, send):
        self.client.post(reverse('employee-registration'), registration_form())
        self.assertTrue(send.call_args.args[1].startswith(f'{SMS_BRAND}: '))

    @patch('home.views.send_sms', return_value=SMSResult(True, 'test'))
    def test_status_updates_name_the_portal(self, send):
        owner = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        employer = Employer.objects.create(employer=owner, company_name='Rawis Store', business_permit_no='BP-1',
                                           contact_no='09170000001', description='d')
        person = User.objects.create_user('maria', 'm@example.com', 'x', role='applicant')
        applicant = Applicant.objects.create(user=person, first_name='Maria', last_name='Cruz', middle_name='',
                                             email='m@example.com', phone_number='09171112222')
        job = JobPost.objects.create(employer=employer, title='Sales Clerk', description='d', qualifications='q',
                                     location='Pio Duran', deadline=timezone.localdate() + timedelta(days=9), status='approved')
        application = JobApplication.objects.create(job=job, applicant=applicant)
        self.client.force_login(owner)
        for status in ['reviewing', 'shortlisted', 'offered']:
            self.client.post(reverse('update-applicant-status', args=[application.pk]), {'status': status})
            self.assertTrue(send.call_args.args[1].startswith(f'{SMS_BRAND}\n\nDear Maria') or
                            send.call_args.args[1].startswith(f'{SMS_BRAND}\n\nYou have a job offer'), status)
