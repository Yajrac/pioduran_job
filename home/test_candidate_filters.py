from datetime import date
from django.test import TestCase
from django.urls import reverse
from user.models import User
from applicant.models import Applicant, WorkExperience
from employer.models import Employer, JobPost, JobApplication


class CandidateFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', role='employer')
        employer = Employer.objects.create(employer=self.owner, company_name='Company', business_permit_no='P', contact_no='09123456789')
        self.job = JobPost.objects.create(employer=employer, title='Store Assistant', description='Customer service and inventory', deadline=date(2030,1,1))
        for i, skills in enumerate(['Customer Service, Inventory Management','Cooking']):
            user = User.objects.create_user(username=f'candidate{i}')
            applicant = Applicant.objects.create(user=user, first_name=f'Candidate{i}', email=f'a{i}@example.com', skills=skills)
            JobApplication.objects.create(job=self.job, applicant=applicant, status='shortlisted' if i == 0 else 'pending')
            if i == 0:
                WorkExperience.objects.create(applicant=applicant, job_title='Store Assistant', company='Sample Store', start_date=date(2024,1,1), is_current=True)
        self.client.force_login(self.owner)
        self.url = reverse('applicants')

    def test_combined_filters_and_explanation(self):
        response = self.client.get(self.url, {'skill':'Inventory','status':'shortlisted','job':self.job.pk})
        self.assertContains(response, 'Candidate0')
        self.assertNotContains(response, 'Candidate1')
        self.assertContains(response, 'Matched skills:')
        self.assertContains(response, 'Store Assistant at Sample Store')
        self.assertEqual(response.context['result_count'], 1)

    def test_filters_apply_automatically_without_experience_filter(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Apply Filters')
        self.assertNotContains(response, 'candidateExperience')
        self.assertContains(response, 'candidate-filters.js')

    def test_foreign_job_and_bad_job_id_do_not_leak_records(self):
        for value in ['999999', 'not-a-number']:
            response = self.client.get(self.url, {'job':value})
            self.assertEqual(response.context['result_count'], 0)

    def test_unknown_skill_has_no_matches(self):
        response = self.client.get(self.url, {'skill':'Welding'})
        self.assertEqual(response.context['result_count'], 0)
