from datetime import date

from django.test import TestCase
from django.urls import reverse

from applicant.models import Applicant, WorkExperience
from employer.models import Employer, JobPost, JobApplication
from user.models import User


class EmployerApplicantProfileTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', role='employer')
        employer = Employer.objects.create(employer=self.owner, company_name='Owner Co', business_permit_no='P1', contact_no='09111111111')
        self.job = JobPost.objects.create(employer=employer, title='Sales Staff', required_skills='Sales, Cashiering', deadline=date(2030, 1, 1))
        self.applicant_user = User.objects.create_user(username='juan', role='applicant')
        self.applicant = Applicant.objects.create(
            user=self.applicant_user, first_name='Juan', last_name='Dela Cruz', middle_name='',
            email='juan@example.com', phone_number='09222222222', skills='Sales, Driving',
        )
        WorkExperience.objects.create(applicant=self.applicant, job_title='Store Clerk', company='Mini Mart', start_date=date(2022, 1, 1), is_current=True)
        self.application = JobApplication.objects.create(job=self.job, applicant=self.applicant)
        self.url = reverse('employer-applicant-profile', args=[self.application.pk])

    def test_job_owner_sees_full_profile(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in ['Juan', 'Dela Cruz', 'juan@example.com', '09222222222', 'Driving', 'Store Clerk', 'Mini Mart', 'Sales Staff']:
            self.assertContains(response, text)
        self.assertContains(response, '1 of 2')
        self.assertContains(response, 'Missing: Cashiering')

    def test_other_employer_gets_404(self):
        other = User.objects.create_user(username='other', role='employer')
        Employer.objects.create(employer=other, company_name='Other Co', business_permit_no='P2', contact_no='09333333333')
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_applicant_cannot_use_employer_page(self):
        self.client.force_login(self.applicant_user)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login-user'), response['Location'])

    def test_applicants_list_links_to_profile(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('applicants'))
        self.assertContains(response, self.url)
