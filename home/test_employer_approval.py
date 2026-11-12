from django.test import TestCase
from django.urls import reverse
from user.models import User
from employer.models import Employer, JobPost


class EmployerApprovalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='company', role='employer')
        self.employer = Employer.objects.create(employer=self.user, company_name='Company', business_permit_no='permit', contact_no='09123456789', approval_status='pending', is_active=False)
        self.admin = User.objects.create_user(username='peso', role='admin')
        self.url = reverse('review-employer', args=[self.employer.pk])

    def test_pending_account_cannot_use_employer_features(self):
        self.client.force_login(self.user)
        for route in ['employer-dashboard','job-list','job-post','applicants']:
            response = self.client.get(reverse(route))
            self.assertRedirects(response, reverse('employer-approval-status'))
        self.client.post(reverse('job-post'), {'title':'Unauthorized job'})
        self.assertFalse(JobPost.objects.exists())
        self.assertContains(self.client.get(reverse('employer-approval-status')), 'Pending Approval')

    def test_only_admin_can_approve(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url, {'decision':'approved'}).status_code, 403)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.approval_status, 'pending')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        response = self.client.post(self.url, {'decision':'approved','remarks':'Permit reviewed.'})
        self.assertEqual(response.status_code, 302)
        self.employer.refresh_from_db()
        self.assertTrue(self.employer.is_active)
        self.assertEqual(self.employer.approval_status, 'approved')
        self.assertIsNotNone(self.employer.reviewed_at)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('employer-dashboard')).status_code, 200)

    def test_rejection_requires_reason_and_displays_remarks(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {'decision':'rejected'})
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.approval_status, 'pending')
        self.client.post(self.url, {'decision':'rejected','remarks':'Please contact PESO about your business permit.'})
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.approval_status, 'rejected')
        self.assertFalse(self.employer.is_active)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('employer-approval-status')), 'Please contact PESO')

    def test_default_preserves_existing_approval_and_suspension_blocks(self):
        self.assertEqual(Employer._meta.get_field('approval_status').default, 'approved')
        self.employer.approval_status = 'approved'
        self.employer.save()
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('employer-dashboard')), reverse('employer-approval-status'))

    def test_pending_cannot_bypass_approval_using_activate(self):
        self.client.force_login(self.admin)
        self.client.get(reverse('suspend_employer', args=[self.employer.pk]))
        self.employer.refresh_from_db()
        self.assertFalse(self.employer.is_active)
        self.assertEqual(self.employer.approval_status, 'pending')

    def test_completed_approval_cannot_be_rejected_or_reviewed_again(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {'decision':'approved', 'remarks':'Reviewed.'})
        self.employer.refresh_from_db()
        reviewed_at = self.employer.reviewed_at
        page = self.client.get(reverse('employer_detail', args=[self.employer.pk]))
        self.assertNotContains(page, 'id="employerReviewForm"')
        self.client.post(self.url, {'decision':'rejected', 'remarks':'Changed mind.'})
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.approval_status, 'approved')
        self.assertEqual(self.employer.approval_remarks, 'Reviewed.')
        self.assertEqual(self.employer.reviewed_at, reviewed_at)
        self.assertTrue(self.employer.is_active)
