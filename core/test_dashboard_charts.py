from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from core.dashboard_charts import _nice_max, employer_status, job_status, monthly_trend
from employer.models import Employer, JobApplication, JobPost
from user.models import User


class DashboardChartTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('pesoadmin', password='x', role='admin')
        statuses = [('approved', True), ('approved', True), ('approved', False), ('pending', False), ('rejected', False)]
        self.employers = []
        for n, (approval, active) in enumerate(statuses):
            owner = User.objects.create_user(f'company{n}', password='x', role='employer')
            self.employers.append(Employer.objects.create(
                employer=owner, company_name=f'C{n}', business_permit_no=f'BP-{n}', contact_no=f'0917000000{n}',
                description='d', approval_status=approval, is_active=active))
        self.job = JobPost.objects.create(employer=self.employers[0], title='Cashier', description='d', qualifications='q',
                                          location='x', deadline=timezone.localdate() + timedelta(days=5),
                                          status='approved', category='sales_retail')
        JobPost.objects.create(employer=self.employers[0], title='Clerk', description='d', qualifications='q',
                               location='x', deadline=timezone.localdate(), status='pending')

    def test_status_splits_count_every_state(self):
        employers = {p['label']: (p['count'], p['share']) for p in employer_status()['parts']}
        self.assertEqual(employers, {'Active': (2, 40), 'Pending approval': (1, 20), 'Suspended': (1, 20), 'Rejected': (1, 20)})
        jobs = job_status()
        self.assertEqual(jobs['total'], 2)
        self.assertEqual([p['count'] for p in jobs['parts']], [1, 1, 0])

    def test_trend_counts_this_month(self):
        user = User.objects.create_user('person', password='x', role='applicant')
        person = Applicant.objects.create(user=user, first_name='A', last_name='B', middle_name='', email='a@b.com',
                                          phone_number='09171111111')
        JobApplication.objects.create(job=self.job, applicant=person, status='hired', hired_at=timezone.now())
        trend = monthly_trend()
        self.assertEqual(len(trend['points']), 6)
        self.assertEqual((trend['last']['applications'], trend['last']['hires']), (1, 1))
        self.assertEqual(trend['ticks'][-1]['value'], 4)

    def test_nice_axis_maximum(self):
        self.assertEqual([_nice_max(v) for v in (0, 3, 9, 23, 140)], [4, 4, 20, 40, 200])

    def test_dashboard_renders_accessible_charts(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('peso-dashboard'))
        for text in ['Applications &amp; Hires', 'View as table', 'Employer Accounts', 'Pending approval',
                     'Job Post Status', 'Most Applied Job Categories', 'class="viz-tooltip"']:
            self.assertContains(response, text)
