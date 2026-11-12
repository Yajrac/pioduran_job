from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from employer.models import Employer
from user.models import User


class EmployerReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='report-owner', role='employer')
        Employer.objects.create(employer=self.user, company_name='Reports Company', business_permit_no='REPORT-1', contact_no='09123456789')
        self.client.force_login(self.user)

    def test_controls_moved_to_reports(self):
        report = self.client.get(reverse('employer-reports'))
        self.assertContains(report, 'Download PDF')
        self.assertContains(report, 'Hiring Date From')
        overview = self.client.get(reverse('employer-dashboard'))
        self.assertNotContains(overview, 'Download PDF')
        self.assertNotContains(overview, 'Hiring Date From')

    @patch('core.report_pdf.download_report')
    def test_export_uses_dates_and_own_company(self, download):
        download.return_value = HttpResponse(b'pdf', content_type='application/pdf')
        response = self.client.get(reverse('employer-reports'), {'export': 'time-to-hire', 'hired_from': '2026-01-01', 'hired_to': '2026-12-31'})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        data = download.call_args.args[1]
        self.assertEqual(data['hired_from'], '2026-01-01')
        self.assertEqual(data['hired'], [])

    @patch('core.report_pdf.download_report')
    def test_invalid_range_does_not_export(self, download):
        response = self.client.get(reverse('employer-reports'), {'export': 'time-to-hire', 'hired_from': '2026-12-31', 'hired_to': '2026-01-01'})
        self.assertContains(response, 'Enter valid dates')
        download.assert_not_called()

    def test_requires_employer_login(self):
        self.user.role = 'applicant'
        self.user.save()
        self.assertEqual(self.client.get(reverse('employer-reports')).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('employer-reports')).status_code, 302)
