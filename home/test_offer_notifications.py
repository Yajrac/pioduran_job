from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from home.sms import SMSResult, SMS_BRAND
from user.models import User


@patch('home.application_actions.send_sms', return_value=SMSResult(True, 'test'))
class OfferResponseNotificationTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        employer = Employer.objects.create(employer=owner, company_name='Rawis Store', business_permit_no='BP-1',
                                           contact_no='09180000001', description='d')
        self.person = User.objects.create_user('maria', 'm@example.com', 'x', role='applicant')
        applicant = Applicant.objects.create(user=self.person, first_name='Maria', last_name='Cruz', middle_name='',
                                             email='m@example.com', phone_number='09171112222')
        job = JobPost.objects.create(employer=employer, title='Sales Clerk', description='d', qualifications='q',
                                     location='Pio Duran', deadline=timezone.localdate() + timedelta(days=9), status='approved')
        self.application = JobApplication.objects.create(job=job, applicant=applicant, status='offered')
        self.client.force_login(self.person)

    def act(self, action):
        return self.client.post(reverse('applicant-application-action', args=[self.application.pk]), {'action': action})

    def test_employer_is_texted_when_the_offer_is_accepted(self, send):
        self.assertRedirects(self.act('accept'), reverse('my-applications'))
        number, text = send.call_args.args
        self.assertEqual(number, '09180000001')
        self.assertTrue(text.startswith(f'{SMS_BRAND}: Maria Cruz ACCEPTED your job offer for Sales Clerk'))

    def test_employer_is_texted_when_the_offer_is_declined(self, send):
        self.act('decline')
        self.assertIn('Maria Cruz DECLINED your job offer for Sales Clerk', send.call_args.args[1])

    def test_no_text_for_withdraw_or_a_rejected_action(self, send):
        self.act('accept')
        send.reset_mock()
        self.act('decline')  # no longer offered -> error, nothing sent
        send.assert_not_called()

    def test_a_failed_sms_does_not_undo_the_answer(self, send):
        send.return_value = SMSResult(False, 'test', 'offline')
        self.act('accept')
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'hired')
