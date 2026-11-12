from datetime import date
from django.test import TestCase
from user.models import User
from applicant.models import Applicant
from .models import Employer, JobPost, JobApplication
from .application_status import change_application_status, applicant_application_action
from django.urls import reverse


class VacancyStatusTests(TestCase):
    def setUp(self):
        owner = User.objects.create(username='owner', role='employer')
        self.employer = Employer.objects.create(employer=owner,company_name='Company',business_permit_no='P1',contact_no='09123456789')
        self.job = JobPost.objects.create(employer=self.employer,title='Role',vacancies=1,deadline=date(2027,1,1))
        self.applications = []
        for i in range(2):
            user = User.objects.create(username=f'applicant{i}')
            applicant = Applicant.objects.create(user=user,email=f'a{i}@example.com')
            self.applications.append(JobApplication.objects.create(job=self.job,applicant=applicant))

    def change(self, index, status):
        return change_application_status(self.applications[index].pk,self.employer.pk,status)

    def test_accept_decrements_once_and_reversal_restores(self):
        self.assertTrue(self.change(0,'accepted'))
        self.assertFalse(self.change(0,'accepted'))
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies,0)
        with self.assertRaises(ValueError): self.change(1,'accepted')
        self.applications[1].refresh_from_db()
        self.assertEqual(self.applications[1].status,'pending')
        self.change(0,'rejected')
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies,1)
        self.change(1,'accepted')
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies,0)

    def test_non_accepted_status_preserves_slots(self):
        self.change(0,'reviewing')
        self.change(0,'shortlisted')
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies,1)

    def test_offer_accept_keeps_reserved_slot_and_records_hire_date(self):
        self.change(0, 'offered')
        application = self.applications[0]
        applicant_application_action(application.pk, application.applicant.user_id, 'accept')
        application.refresh_from_db()
        self.job.refresh_from_db()
        self.assertEqual(application.status, 'hired')
        self.assertIsNotNone(application.hired_at)
        self.assertEqual(self.job.vacancies, 0)
        with self.assertRaises(ValueError):
            applicant_application_action(application.pk, application.applicant.user_id, 'accept')

    def test_decline_restores_slot_once_and_employer_cannot_reopen(self):
        self.change(0, 'offered')
        application = self.applications[0]
        applicant_application_action(application.pk, application.applicant.user_id, 'decline')
        with self.assertRaises(ValueError):
            applicant_application_action(application.pk, application.applicant.user_id, 'decline')
        with self.assertRaises(ValueError):
            self.change(0, 'reviewing')
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies, 1)

    def test_withdraw_is_owner_only_post_only_and_terminal(self):
        application = self.applications[0]
        url = reverse('applicant-application-action', args=[application.pk])
        self.client.force_login(self.applications[1].applicant.user)
        self.assertEqual(self.client.post(url, {'action':'withdraw'}).status_code, 404)
        self.client.force_login(application.applicant.user)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'action':'withdraw'}).status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, 'withdrawn')
        self.job.refresh_from_db()
        self.assertEqual(self.job.vacancies, 1)
        with self.assertRaises(ValueError):
            self.change(0, 'offered')

    def test_accept_without_offer_is_rejected(self):
        application = self.applications[0]
        with self.assertRaises(ValueError):
            applicant_application_action(application.pk, application.applicant.user_id, 'accept')
