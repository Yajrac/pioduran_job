from datetime import date, datetime
from io import BytesIO
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader
from user.models import User
from applicant.models import Applicant
from employer.models import Employer, JobPost, JobApplication


class HiredReportTests(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username='admin', role='admin')
        owner = User.objects.create_user(username='company', role='employer')
        employer = Employer.objects.create(employer=owner, company_name='Test Company', business_permit_no='permit', contact_no='09123456789')
        job = JobPost.objects.create(employer=employer, title='Sales Assistant', deadline=date(2030, 1, 1))
        for i, status in enumerate(['hired', 'offered', 'declined', 'withdrawn', 'pending']):
            user = User.objects.create_user(username=f'person{i}')
            applicant = Applicant.objects.create(user=user, email=f'p{i}@example.com', first_name=f'Person{i}', last_name='Example')
            JobApplication.objects.create(job=job, applicant=applicant, status=status, hired_at=datetime(2026, 11, 8, 0, 30, tzinfo=ZoneInfo('Asia/Manila')) if status == 'hired' else None)
        self.client.force_login(admin)
        self.url = reverse('reports')

    def test_only_hired_records_are_included(self):
        response = self.client.get(self.url, {'section':'hired'})
        self.assertEqual(response.context['hired_kpis']['total'], 1)
        self.assertContains(response, 'Total hired')
        self.assertContains(response, 'Person0')
        self.assertNotContains(response, 'Person1')

    def test_days_label_is_human_readable(self):
        from core.templatetags.admin_format import days_label
        self.assertEqual([days_label(v) for v in (None, 0, 0.4, 1, 1.04, 6.5, 12)],
                         ['Not available', 'Same day', 'Same day', '1 day', '1 day', '6.5 days', '12 days'])

    def test_hiring_date_filter_includes_entire_local_day(self):
        response = self.client.get(self.url, {'section':'hired', 'hired_from':'2026-11-08', 'hired_to':'2026-11-08'})
        self.assertEqual(response.context['hired_kpis']['total'], 1)
        response = self.client.get(self.url, {'section':'hired', 'hired_from':'2026-11-09'})
        self.assertEqual(response.context['hired_kpis']['total'], 0)
        self.assertContains(response, 'No hired applicants for this period.')

    def test_pdf_contains_matching_hired_records(self):
        response = self.client.get(self.url, {'section':'hired','export':'hired'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('Person0 Example', text)
        self.assertIn('Records: 1', text)
        self.assertNotIn('Person1', text)

    def test_invalid_range_does_not_download_misleading_pdf(self):
        response = self.client.get(self.url, {'section':'hired','export':'hired','hired_from':'2027-01-01','hired_to':'2026-01-01'})
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertContains(response, 'Enter valid dates')

    def test_non_admin_cannot_access_reports(self):
        self.client.force_login(User.objects.get(username='person0'))
        self.assertEqual(self.client.get(self.url, {'section':'hired','export':'hired'}).status_code, 403)

    def test_employer_dashboard_and_pdf_have_own_hiring_analytics(self):
        self.client.force_login(User.objects.get(username='company'))
        response = self.client.get(reverse('employer-dashboard'))
        self.assertContains(response, 'Time to Hire')
        self.assertIn('hiring_stats', response.context)
        response = self.client.get(reverse('employer-reports'), {'export':'pdf'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('Time to Hire', text)
        self.assertIn('Per Job Post', text)

    def test_admin_pdf_includes_duration_column_and_analytics(self):
        response = self.client.get(self.url, {'section':'hired','export':'hired'})
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('Days to Hire', text)
        self.assertIn('Time-to-Hire Analytics', text)
