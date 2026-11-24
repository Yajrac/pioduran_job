from django.test import TestCase
from django.urls import reverse
from user.models import User
from employer.models import Employer


class CompanyProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', role='employer', email='owner@example.com')
        self.company = Employer.objects.create(employer=self.user, company_name='Company', business_permit_no='BP-1', contact_no='09123456789', description='Original', company_logo='company_logo/original.png')
        self.other = User.objects.create_user(username='other', role='employer', email='other@example.com')
        self.other_company = Employer.objects.create(employer=self.other, company_name='Other Company', business_permit_no='BP-2', contact_no='09987654321', description='Other')
        self.client.force_login(self.user)

    def payload(self, **changes):
        data = dict(company_name='Updated Company', contact_no='09123456789', description='Updated description of the company.', email='new@example.com')
        data.update(changes)
        return data

    def test_save_updates_own_profile_and_retains_logo(self):
        response = self.client.post(reverse('edit-employer-company-profile'), self.payload(id=self.other_company.pk, employer=self.other.pk))
        self.assertRedirects(response, reverse('employer-company-profile'))
        self.company.refresh_from_db()
        self.user.refresh_from_db()
        self.other_company.refresh_from_db()
        self.assertEqual(self.company.company_name, 'Updated Company')
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(self.company.company_logo.name, 'company_logo/original.png')
        self.assertEqual(self.other_company.company_name, 'Other Company')

    def test_duplicate_and_invalid_fields_do_not_save(self):
        response = self.client.post(reverse('edit-employer-company-profile'), self.payload(company_name='Other Company', email='other@example.com', contact_no='-123'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Company name is already registered.')
        self.assertContains(response, 'Email address is already registered.')
        self.assertContains(response, 'starting with 09')
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, 'Company')

    def test_applicant_cannot_edit_company(self):
        applicant = User.objects.create_user(username='applicant', role='applicant')
        self.client.force_login(applicant)
        self.assertEqual(self.client.get(reverse('edit-employer-company-profile')).status_code, 403)

    def test_company_view_and_form_load(self):
        # Avoid requiring a real media file: template only emits its URL.
        self.assertEqual(self.client.get(reverse('employer-company-profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('edit-employer-company-profile')).status_code, 200)


class CompanyProfileSummaryTests(TestCase):
    def test_stats_checklist_and_status_badge(self):
        from datetime import timedelta
        from django.utils import timezone
        from employer.models import Employer, JobPost
        from user.models import User
        owner = User.objects.create_user('summaryco', email='hr@summary.example', password='x', role='employer')
        employer = Employer.objects.create(employer=owner, company_name='Summary Co', business_permit_no='BP-S1',
                                           contact_no='09170000999', description='Short')
        JobPost.objects.create(employer=employer, title='Clerk', description='d', qualifications='q', location='x',
                               deadline=timezone.localdate() + timedelta(days=5), status='approved')
        self.client.force_login(owner)
        response = self.client.get(reverse('employer-company-profile'))
        self.assertEqual(response.context['stats']['active_jobs'], 1)
        self.assertEqual(response.context['completeness'], 50)  # no logo, short description
        self.assertTrue(response.context['about_too_short'])
        self.assertContains(response, 'Approved &middot; Active')
        self.assertContains(response, 'Recent job posts')
