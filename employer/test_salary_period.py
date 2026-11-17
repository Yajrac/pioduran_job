from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from employer.models import Employer, JobPost
from user.models import User


class SalaryPeriodTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        self.employer = Employer.objects.create(employer=self.owner, company_name='Rawis Store', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d')
        self.client.force_login(self.owner)
        self.data = {
            'title': 'Sales Clerk', 'description': 'Assist customers.', 'qualifications': 'At least high school graduate',
            'location': 'Brgy. Rawis, Pio Duran, Albay', 'job_type': 'full_time', 'category': 'sales_retail',
            'vacancies': '2', 'deadline': (timezone.localdate() + timedelta(days=20)).isoformat(),
            'salary': '450', 'salary_period': 'day',
        }

    def test_period_is_saved_and_shown(self):
        self.client.post(reverse('job-post'), self.data)
        job = JobPost.objects.get()
        self.assertEqual(job.salary_period, 'day')
        self.assertEqual(job.salary_display, '₱450.00 / day')
        self.assertEqual(job.salary_monthly_estimate, 450 * 26)

    def test_monthly_is_the_default(self):
        self.client.post(reverse('job-post'), {**self.data, 'salary': '12000', 'salary_period': ''})
        self.assertEqual(JobPost.objects.get().salary_display, '₱12,000.00 / month')

    def test_unknown_period_is_rejected(self):
        self.client.post(reverse('job-post'), {**self.data, 'salary_period': 'year'})
        self.assertFalse(JobPost.objects.exists())

    def test_form_has_period_choice_and_qualification_picker(self):
        page = self.client.get(reverse('job-post'))
        self.assertContains(page, 'name="salary_period"')
        self.assertContains(page, 'id="qualification_pick"')
        self.assertContains(page, '3 to 5')


class OtherCategoryAndDeadlineTests(SalaryPeriodTests):
    def test_other_category_needs_text_and_is_shown_as_the_label(self):
        self.client.post(reverse('job-post'), {**self.data, 'category': 'other', 'category_other': ''})
        self.assertFalse(JobPost.objects.exists())
        self.client.post(reverse('job-post'), {**self.data, 'category': 'other', 'category_other': '  Event   Staff '})
        job = JobPost.objects.get()
        self.assertEqual(job.category_other, 'Event Staff')
        self.assertEqual(job.category_label, 'Event Staff')

    def test_typed_text_is_ignored_for_normal_categories(self):
        self.client.post(reverse('job-post'), {**self.data, 'category_other': 'Something'})
        job = JobPost.objects.get()
        self.assertEqual(job.category_other, '')
        self.assertEqual(job.category_label, 'Sales & Retail')

    def test_past_deadline_is_rejected_and_picker_starts_today(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.client.post(reverse('job-post'), {**self.data, 'deadline': yesterday})
        self.assertContains(response, 'Application deadline cannot be in the past.')
        self.assertFalse(JobPost.objects.exists())
        page = self.client.get(reverse('job-post'))
        self.assertContains(page, f'min="{timezone.localdate().isoformat()}"')
        self.client.post(reverse('job-post'), {**self.data, 'deadline': timezone.localdate().isoformat()})
        self.assertTrue(JobPost.objects.exists())


class ReviewAndConfirmationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('shop', 'h@example.com', 'x', role='employer')
        Employer.objects.create(employer=self.owner, company_name='Rawis Shop', business_permit_no='BP-9',
                                contact_no='09170000009', description='d')
        self.client.force_login(self.owner)
        self.data = {
            'title': 'Store Helper', 'description': 'Help in the store.', 'qualifications': 'Physically fit',
            'location': 'Brgy. Rawis, Pio Duran, Albay', 'job_type': 'full_time', 'category': 'sales_retail',
            'vacancies': '1', 'deadline': (timezone.localdate() + timedelta(days=9)).isoformat(),
        }

    def test_form_has_review_dialog(self):
        page = self.client.get(reverse('job-post'))
        self.assertContains(page, 'id="reviewDialog"')
        self.assertContains(page, 'Review job')
        self.assertContains(page, 'Submit for approval')

    def test_after_submitting_the_job_list_says_it_waits_for_approval(self):
        response = self.client.post(reverse('job-post'), self.data, follow=True)
        self.assertContains(response, 'was submitted. It is waiting for PESO approval')
        self.assertEqual(JobPost.objects.get().status, 'pending')

    def test_editing_a_published_job_explains_re_approval(self):
        self.client.post(reverse('job-post'), self.data)
        job = JobPost.objects.get()
        job.status = 'approved'
        job.save()
        page = self.client.get(reverse('update-job', args=[job.pk]))
        self.assertContains(page, 'Save and resubmit')
        response = self.client.post(reverse('update-job', args=[job.pk]), {**self.data, 'title': 'Senior Store Helper'}, follow=True)
        self.assertContains(response, 'hidden until PESO approves it again')
