from datetime import date
from django.test import TestCase
from django.urls import reverse
from user.models import User
from applicant.models import Applicant
from employer.models import Employer, JobPost, JobApplication, ApplicantAssessment


class AssessmentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', role='employer')
        self.employer = Employer.objects.create(employer=self.owner, company_name='Company', business_permit_no='P', contact_no='09123456789')
        user = User.objects.create_user(username='candidate')
        self.applicant = Applicant.objects.create(user=user, email='a@example.com', skills='Sales')
        self.job = JobPost.objects.create(employer=self.employer, title='Sales Staff', required_skills='Sales', deadline=date(2030,1,1))
        self.application = JobApplication.objects.create(job=self.job, applicant=self.applicant)
        self.url = reverse('review-applicant', args=[self.application.pk])
        self.client.force_login(self.owner)

    def test_scores_are_optional_and_range_checked(self):
        for field in ['skills_score', 'interview_score']:
            response = self.client.post(self.url, {'section':'assessment', field:-1})
            self.assertContains(response, 'Score cannot be negative.')
            self.assertFalse(ApplicantAssessment.objects.exists())
            response = self.client.post(self.url, {'section':'assessment', field:'2.5'})
            self.assertContains(response, 'Enter a whole number from 0 to 5.')
        response = self.client.post(self.url, {'section':'assessment','skills_score':6})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ApplicantAssessment.objects.exists())
        response = self.client.post(self.url, {'section':'assessment','skills_score':0,'assessment_notes':'Task not demonstrated.'})
        self.assertEqual(response.status_code, 302)
        item = ApplicantAssessment.objects.get()
        self.assertEqual(item.skills_score, 0)
        self.assertIsNone(item.interview_score)

    def test_only_owning_employer_can_review(self):
        stranger = User.objects.create_user(username='stranger', role='employer')
        Employer.objects.create(employer=stranger, business_permit_no='P2', contact_no='09999999999')
        self.client.force_login(stranger)
        self.assertEqual(self.client.post(self.url, {'section':'assessment','skills_score':4}).status_code, 404)

    def test_outcomes_require_hired_status_and_real_dates(self):
        data = {'section':'outcome','outcome':'passed','started_on':'2026-01-01','evaluated_on':'2026-04-01','outcome_notes':'Met job standards.'}
        self.client.post(self.url, data)
        self.assertFalse(ApplicantAssessment.objects.exists())
        self.application.status = 'hired'
        self.application.save()
        self.client.post(self.url, {**data,'evaluated_on':'2025-01-01'})
        self.assertFalse(ApplicantAssessment.objects.exists())
        self.client.post(self.url, data)
        self.assertEqual(ApplicantAssessment.objects.get().outcome, 'passed')

    def test_snapshot_is_not_replaced_by_later_profile_changes(self):
        self.applicant.skills = 'Cooking'
        self.applicant.save()
        self.application.status = 'reviewing'
        self.application.save()
        self.application.refresh_from_db()
        self.assertEqual(self.application.application_snapshot['skills'], 'Sales')

    def test_success_modal_shown_once_only_after_valid_save(self):
        response = self.client.post(self.url, {'section':'assessment','skills_score':4,'interview_score':4}, follow=True)
        self.assertContains(response, 'id="assessmentSavedDialog"')
        self.assertContains(response, 'Assessment saved successfully.')
        self.assertContains(response, 'Back to Applicants')
        self.assertNotContains(self.client.get(self.url), 'id="assessmentSavedDialog"')
        response = self.client.post(self.url, {'section':'assessment','skills_score':-1})
        self.assertNotContains(response, 'id="assessmentSavedDialog"')

    def test_admin_summary_keeps_missing_outcome_unknown(self):
        self.application.status = 'hired'
        self.application.save()
        admin = User.objects.create_user(username='admin', role='admin')
        self.client.force_login(admin)
        response = self.client.get(reverse('reports'), {'section':'assessments'})
        self.assertEqual(response.context['assessment_summary']['not_evaluated'], 1)
        self.assertEqual(response.context['assessment_summary']['failed'], 0)


class OutcomeDateTests(TestCase):
    def setUp(self):
        from datetime import datetime, time, timedelta
        from django.utils import timezone
        self.owner = User.objects.create_user(username='owner2', role='employer')
        employer = Employer.objects.create(employer=self.owner, company_name='Co', business_permit_no='P9', contact_no='09123450000')
        user = User.objects.create_user(username='worker')
        applicant = Applicant.objects.create(user=user, email='w@example.com', skills='Sales')
        job = JobPost.objects.create(employer=employer, title='Clerk', required_skills='Sales', deadline=date(2030, 1, 1))
        self.hired_on = timezone.localdate() - timedelta(days=100)
        self.application = JobApplication.objects.create(
            job=job, applicant=applicant, status='hired',
            hired_at=timezone.make_aware(datetime.combine(self.hired_on, time(9))))
        self.url = reverse('review-applicant', args=[self.application.pk])
        self.client.force_login(self.owner)
        self.timedelta = timedelta

    def post(self, start, evaluated=None, outcome='passed'):
        return self.client.post(self.url, {'section': 'outcome', 'outcome': outcome,
                                           'started_on': start.isoformat() if start else '',
                                           'evaluated_on': evaluated.isoformat() if evaluated else '',
                                           'outcome_notes': 'Met the targets.'})

    def test_start_cannot_be_before_the_hire_date(self):
        response = self.post(self.hired_on - self.timedelta(days=1), self.hired_on + self.timedelta(days=60))
        self.assertContains(response, 'cannot be earlier than the hire date')
        self.assertFalse(ApplicantAssessment.objects.filter(outcome='passed').exists())

    def test_valid_dates_are_saved(self):
        response = self.post(self.hired_on + self.timedelta(days=3), self.hired_on + self.timedelta(days=93))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ApplicantAssessment.objects.get().outcome, 'passed')

    def test_calendar_limits_are_set(self):
        page = self.client.get(self.url)
        self.assertContains(page, f'min="{self.hired_on.isoformat()}"')
        self.assertNotContains(page, 'Probation length')
