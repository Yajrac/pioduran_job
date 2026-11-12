from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.job_categories import guess_category
from employer.job_demand import demand_ranking, likelihood, success_history, top_jobs
from employer.models import Employer, JobApplication, JobPost
from user.models import User


class JobDemandTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('company', password='x', role='employer')
        self.employer = Employer.objects.create(employer=owner, company_name='Acme', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d')
        self.admin = User.objects.create_user('pesoadmin', password='x', role='admin')
        deadline = timezone.localdate() + timedelta(days=10)
        self.sales = JobPost.objects.create(employer=self.employer, title='Sales Staff', description='d', qualifications='q',
                                            location='Pio Duran', deadline=deadline, status='approved', category='sales_retail', vacancies=3)
        self.cook = JobPost.objects.create(employer=self.employer, title='Cook', description='d', qualifications='q',
                                           location='Pio Duran', deadline=deadline, status='approved', category='food_service')
        self.people = [self.make_applicant(n) for n in range(8)]

    def make_applicant(self, n):
        user = User.objects.create_user(f'person{n}', password='x', role='applicant')
        return Applicant.objects.create(user=user, first_name=f'P{n}', last_name='X', middle_name='',
                                        email=f'p{n}@example.com', phone_number=f'0917100000{n}')

    def apply(self, job, person, status='pending'):
        return JobApplication.objects.create(job=job, applicant=person, status=status)

    def test_guess_category_from_title(self):
        self.assertEqual(guess_category('Store Assistant / Ice Candy Sales Staff'), 'sales_retail')
        self.assertEqual(guess_category('Sales Staff / LPG Delivery Helper'), 'driving_delivery')
        self.assertEqual(guess_category('Head Cook'), 'food_service')
        self.assertEqual(guess_category('vc'), 'other')

    def test_most_applied_category_ranks_first(self):
        for person in self.people[:5]:
            self.apply(self.sales, person)
        for person in self.people[5:7]:
            self.apply(self.cook, person)
        ranking = demand_ranking()
        self.assertEqual([row['category'] for row in ranking], ['sales_retail', 'food_service'])
        self.assertEqual((ranking[0]['rank'], ranking[0]['applications'], ranking[0]['percent']), (1, 5, 100))
        self.assertEqual(ranking[0]['trend'], 'up')
        self.assertEqual(ranking[0]['open_vacancies'], 3)
        self.assertEqual(top_jobs()[0], self.sales)

    def test_success_rate_ignores_withdrawn_and_declined(self):
        statuses = ['hired', 'rejected', 'rejected', 'withdrawn', 'declined']
        for person, status in zip(self.people, statuses):
            self.apply(self.sales, person, status)
        row = demand_ranking()[0]
        self.assertEqual((row['hires'], row['finished'], row['success_rate']), (1, 3, 33.3))

    def test_likelihood_needs_enough_history_and_excludes_itself(self):
        finished = [self.apply(self.sales, person, status) for person, status in
                    zip(self.people, ['hired', 'hired', 'rejected', 'rejected', 'rejected'])]
        new = self.apply(self.sales, self.people[6])
        result = likelihood(new, success_history())
        self.assertEqual((result['percent'], result['sample']), (40.0, 5))
        # A finished application is not counted in its own estimate -> only 4 left.
        self.assertIsNone(likelihood(finished[0], success_history()))
        self.assertIsNone(likelihood(self.apply(self.cook, self.people[7]), success_history()))

    def test_demand_report_page_and_pdf(self):
        self.apply(self.sales, self.people[0])
        self.client.force_login(self.admin)
        url = reverse('reports')
        response = self.client.get(url, {'section': 'demand'})
        self.assertContains(response, 'Job Demand Ranking')
        self.assertContains(response, 'Sales &amp; Retail')
        response = self.client.get(url, {'section': 'demand', 'export': 'demand'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        response = self.client.get(url, {'section': 'demand', 'demand_from': '2030-01-01', 'demand_to': '2020-01-01'})
        self.assertContains(response, 'Enter valid dates')
        self.assertContains(self.client.get(reverse('peso-dashboard')), 'Most Applied Job Categories')

    def test_employer_sees_likelihood_on_applicants_page(self):
        self.apply(self.sales, self.people[0])
        self.client.force_login(self.employer.employer)
        response = self.client.get(reverse('applicants'), {'sort': 'likelihood'})
        self.assertContains(response, 'Likelihood of success: not enough data yet')
