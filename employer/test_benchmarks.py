from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant, WorkExperience
from employer.benchmarks import build_benchmarks, compare
from employer.models import ApplicantAssessment, Employer, JobApplication, JobPost
from user.models import User


class BenchmarkTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('company', password='x', role='employer')
        self.employer = Employer.objects.create(employer=owner, company_name='Acme', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d')
        self.job = JobPost.objects.create(employer=self.employer, title='Sales Staff', description='d', qualifications='q',
                                          location='Pio Duran', deadline=timezone.localdate() + timedelta(days=9),
                                          status='approved', category='sales_retail', required_skills='Sales, Cashiering')
        self.count = 0

    def person(self, skills, experience=False):
        self.count += 1
        user = User.objects.create_user(f'p{self.count}', password='x', role='applicant')
        applicant = Applicant.objects.create(user=user, first_name='P', last_name='X', middle_name='', skills=skills,
                                             email=f'p{self.count}@example.com', phone_number=f'091710000{self.count:02d}')
        if experience:
            WorkExperience.objects.create(applicant=applicant, job_title='Sales Clerk', company='Shop',
                                          start_date=timezone.localdate() - timedelta(days=400),
                                          end_date=timezone.localdate() - timedelta(days=30))
        return applicant

    def hired(self, skills, outcome, skills_score=4, interview_score=4, experience=True):
        application = JobApplication.objects.create(job=self.job, applicant=self.person(skills, experience), status='hired')
        ApplicantAssessment.objects.create(application=application, outcome=outcome, skills_score=skills_score,
                                           interview_score=interview_score, started_on=timezone.localdate(),
                                           evaluated_on=timezone.localdate())
        return application

    def test_benchmark_needs_three_passed(self):
        self.hired('Sales, Cashiering', 'passed')
        self.hired('Sales', 'passed')
        self.assertFalse(build_benchmarks()['sales_retail']['ready'])
        self.hired('Sales, Customer Service', 'passed')
        self.hired('Driving', 'failed', 1, 2)
        bench = build_benchmarks()['sales_retail']
        self.assertTrue(bench['ready'])
        self.assertEqual((bench['passed'], bench['failed'], bench['pass_rate']), (3, 1, 75.0))
        self.assertEqual((bench['skills_average'], bench['interview_average']), (4.0, 4.0))
        self.assertEqual(bench['common_skills'][0], ('Sales', 100))
        self.assertEqual(bench['experience_share'], 100)

    def test_compare_above_and_below(self):
        for _ in range(3):
            self.hired('Sales, Cashiering', 'passed')
        benchmarks = build_benchmarks()
        strong = JobApplication.objects.create(job=self.job, applicant=self.person('Sales, Cashiering', True))
        weak = JobApplication.objects.create(job=self.job, applicant=self.person('Welding', False))
        good = compare(strong, benchmarks, 100, ['Sales', 'Cashiering'], ['exp'])
        bad = compare(weak, benchmarks, 0, ['Welding'], [])
        self.assertEqual(good['overall'], 'above')
        self.assertEqual(bad['overall'], 'below')
        self.assertIn('3 employees who passed probation in Sales & Retail', good['basis'])

    def test_no_benchmark_for_other_category(self):
        for _ in range(3):
            self.hired('Sales', 'passed')
        other = JobPost.objects.create(employer=self.employer, title='Cook', description='d', qualifications='q',
                                       location='x', deadline=timezone.localdate(), category='food_service')
        application = JobApplication.objects.create(job=other, applicant=self.person('Cooking'))
        self.assertIsNone(compare(application, build_benchmarks(), 50, ['Cooking'], []))

    def test_report_and_applicants_page(self):
        for _ in range(3):
            self.hired('Sales, Cashiering', 'passed')
        JobApplication.objects.create(job=self.job, applicant=self.person('Sales, Cashiering', True))
        admin = User.objects.create_user('pesoadmin', password='x', role='admin')
        self.client.force_login(admin)
        response = self.client.get(reverse('reports'), {'section': 'assessments'})
        self.assertContains(response, 'Performance Benchmarks by Job Category')
        self.assertContains(response, 'Sales &amp; Retail')
        self.client.force_login(self.employer.employer)
        response = self.client.get(reverse('applicants'))
        self.assertContains(response, 'Above benchmark')
