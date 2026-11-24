from datetime import date, datetime
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from user.models import User


def aware(y, m, d):
    return timezone.make_aware(datetime(y, m, d, 10, 0))


class EmployerReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='report-owner', role='employer')
        self.employer = Employer.objects.create(employer=self.user, company_name='Reports Company', business_permit_no='REPORT-1', contact_no='09123456789')
        self.client.force_login(self.user)

    def make_job(self, title, posted, employer=None):
        job = JobPost.objects.create(employer=employer or self.employer, title=title, deadline=date(2030, 1, 1))
        JobPost.objects.filter(pk=job.pk).update(created_at=posted)
        return job

    def apply(self, job, n, status, applied, hired=None):
        user = User.objects.create_user(username=f'app{n}', role='applicant')
        person = Applicant.objects.create(user=user, first_name='A', last_name=str(n), email=f'a{n}@example.com')
        app = JobApplication.objects.create(job=job, applicant=person, status=status)
        JobApplication.objects.filter(pk=app.pk).update(applied_at=applied, hired_at=hired)

    def seed(self):
        sales = self.make_job('Sales Staff', aware(2026, 3, 1))
        cook = self.make_job('Cook', aware(2025, 6, 1))
        self.apply(sales, 1, 'pending', aware(2026, 3, 5))
        self.apply(sales, 2, 'rejected', aware(2026, 3, 6))
        self.apply(sales, 3, 'hired', aware(2026, 3, 7), hired=aware(2026, 3, 20))
        self.apply(cook, 4, 'rejected', aware(2025, 6, 10))
        other_user = User.objects.create_user(username='other-co', role='employer')
        other = Employer.objects.create(employer=other_user, company_name='Other', business_permit_no='O-1', contact_no='09999999999')
        self.apply(self.make_job('Other Job', aware(2026, 3, 1), other), 5, 'hired', aware(2026, 3, 2), hired=aware(2026, 3, 3))

    def test_counts_all_time(self):
        self.seed()
        totals = self.client.get(reverse('employer-reports')).context['report']['totals']
        self.assertEqual(totals, {'job_posts': 2, 'applications': 4, 'in_progress': 1, 'rejected': 2, 'hired': 1})

    def test_counts_within_dates(self):
        self.seed()
        response = self.client.get(reverse('employer-reports'), {'date_from': '2026-01-01', 'date_to': '2026-12-31'})
        self.assertEqual(response.context['report']['totals'], {'job_posts': 1, 'applications': 3, 'in_progress': 1, 'rejected': 1, 'hired': 1})
        self.assertEqual([job.title for job in response.context['report']['rows']], ['Sales Staff'])
        self.assertContains(response, 'Sales Staff')
        self.assertNotContains(response, 'Other Job')

    def test_page_shows_controls_not_on_overview(self):
        report = self.client.get(reverse('employer-reports'))
        self.assertContains(report, 'Download PDF')
        self.assertContains(report, 'Date From')
        overview = self.client.get(reverse('employer-dashboard'))
        self.assertNotContains(overview, 'Download PDF')

    @patch('core.report_pdf.download_employer_report')
    def test_export_uses_dates_and_own_company(self, download):
        self.seed()
        download.return_value = HttpResponse(b'pdf', content_type='application/pdf')
        response = self.client.get(reverse('employer-reports'), {'export': 'pdf', 'date_from': '2026-01-01', 'date_to': '2026-12-31'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        data = download.call_args.args[0]
        self.assertEqual(data['date_from'], '2026-01-01')
        self.assertEqual(data['report']['totals']['hired'], 1)

    def test_real_pdf_builds(self):
        self.seed()
        response = self.client.get(reverse('employer-reports'), {'export': 'pdf'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    @patch('core.report_pdf.download_employer_report')
    def test_invalid_range_does_not_export(self, download):
        response = self.client.get(reverse('employer-reports'), {'export': 'pdf', 'date_from': '2026-12-31', 'date_to': '2026-01-01'})
        self.assertContains(response, 'Enter valid dates')
        download.assert_not_called()

    def test_requires_employer_login(self):
        self.user.role = 'applicant'
        self.user.save()
        self.assertEqual(self.client.get(reverse('employer-reports')).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('employer-reports')).status_code, 302)
