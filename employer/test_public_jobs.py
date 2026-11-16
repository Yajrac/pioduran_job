from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from user.models import User


class SuspendedEmployerJobsTests(TestCase):
    """Suspending an employer hides their jobs everywhere public; activating restores them."""

    def setUp(self):
        owner = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        self.employer = Employer.objects.create(employer=owner, company_name='Rawis Store', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d')
        self.job = JobPost.objects.create(employer=self.employer, title='Sales Clerk', description='d', qualifications='q',
                                          location='Pio Duran', deadline=timezone.localdate() + timedelta(days=9),
                                          status='approved')
        self.person = User.objects.create_user('maria', 'm@example.com', 'x', role='applicant')
        Applicant.objects.create(user=self.person, first_name='Maria', last_name='Cruz', middle_name='',
                                 email='m@example.com', phone_number='09171112222')

    def suspend(self):
        self.employer.is_active = False
        self.employer.save()

    def test_active_employer_jobs_are_public(self):
        self.assertIn(self.job, JobPost.objects.public())
        self.assertContains(self.client.get(reverse('browse-job')), 'Sales Clerk')
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 200)

    def test_suspended_employer_jobs_are_hidden_everywhere(self):
        self.suspend()
        self.assertNotIn(self.job, JobPost.objects.public())
        self.assertNotContains(self.client.get(reverse('browse-job')), 'Sales Clerk')
        self.assertNotContains(self.client.get(reverse('home')), 'Sales Clerk')
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('company_profile', args=[self.employer.pk])).status_code, 404)

    def test_cannot_apply_to_a_suspended_employer(self):
        self.suspend()
        self.client.force_login(self.person)
        self.client.post(reverse('apply-job', args=[self.job.pk]), {'message': 'hi'})
        self.assertFalse(JobApplication.objects.exists())

    def test_admin_still_sees_the_job_and_activation_restores_it(self):
        self.suspend()
        admin = User.objects.create_user('pesoadmin', 'a@example.com', 'x', role='admin')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 200)
        self.client.logout()
        self.employer.is_active = True
        self.employer.save()
        self.assertContains(self.client.get(reverse('browse-job')), 'Sales Clerk')
