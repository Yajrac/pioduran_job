import shutil
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from user.models import User

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class AccessControlTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_user('pesoadmin', password='x', role='admin')
        self.company_user = User.objects.create_user('company', password='x', role='employer')
        self.other_company_user = User.objects.create_user('other', password='x', role='employer')
        self.person_user = User.objects.create_user('person', password='x', role='applicant')
        self.employer = Employer.objects.create(employer=self.company_user, company_name='Acme',
            business_permit_no='BP-1', contact_no='09170000001', description='d')
        Employer.objects.create(employer=self.other_company_user, company_name='Other',
            business_permit_no='BP-2', contact_no='09170000002', description='d')
        self.applicant = Applicant.objects.create(user=self.person_user, first_name='Ana', last_name='Cruz',
            middle_name='', email='ana@example.com', phone_number='09170000003')
        self.applicant.resume.save('cv.pdf', ContentFile(b'%PDF-1.4 resume'))
        self.job = JobPost.objects.create(employer=self.employer, title='Cashier', description='d',
            qualifications='q', location='Pio Duran', deadline=timezone.localdate() + timedelta(days=5),
            status='approved')
        self.application = JobApplication.objects.create(job=self.job, applicant=self.applicant)

    def test_non_admin_cannot_use_peso_pages(self):
        for user in [self.company_user, self.person_user]:
            self.client.force_login(user)
            for name, args in [('peso-dashboard', []), ('employer-list', []), ('applicant-list', []),
                               ('employer_detail', [self.employer.pk]), ('job-post-list', [])]:
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
            response = self.client.post(reverse('delete_employer', args=[self.employer.pk]))
            self.assertEqual(response.status_code, 403)
        self.assertTrue(Employer.objects.filter(pk=self.employer.pk).exists())

    def test_destructive_admin_actions_require_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('delete_employer', args=[self.employer.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('suspend_employer', args=[self.employer.pk])).status_code, 405)
        self.assertTrue(Employer.objects.filter(pk=self.employer.pk).exists())

    def test_admin_can_reject_job_with_remarks(self):
        self.client.force_login(self.admin)
        self.job.status = 'pending'
        self.job.save()
        self.client.post(reverse('approved-job', args=[self.job.pk]), {'decision': 'reject', 'remarks': 'Add salary.'})
        self.job.refresh_from_db()
        self.assertEqual((self.job.status, self.job.admin_remarks), ('rejected', 'Add salary.'))

    def test_resume_access(self):
        url = reverse('application-document', args=[self.application.pk, 'resume'])
        for user, status in [(self.person_user, 200), (self.company_user, 200), (self.admin, 200),
                             (self.other_company_user, 404)]:
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status, user.username)
            if status == 200:
                response.close()

    def test_private_media_not_served_directly(self):
        from job_portal.urls import public_media
        from django.http import Http404
        from django.test import RequestFactory
        request = RequestFactory().get('/')
        for path in [self.applicant.resume.name, 'Resume/cv.pdf', 'x/../resume/cv.pdf']:
            with self.assertRaises(Http404):
                public_media(request, path)

    def test_unapproved_job_hidden_from_public(self):
        self.job.status = 'pending'
        self.job.save()
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 404)
        self.client.force_login(self.company_user)
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 200)

    def test_editing_approved_job_requires_reapproval(self):
        self.client.force_login(self.company_user)
        self.client.post(reverse('update-job', args=[self.job.pk]), {
            'title': 'Senior Cashier', 'description': 'd', 'qualifications': 'q', 'location': 'Pio Duran',
            'job_type': 'full_time', 'category': 'sales_retail', 'vacancies': '2', 'deadline': (timezone.localdate() + timedelta(days=9)).isoformat(),
        })
        self.job.refresh_from_db()
        self.assertEqual((self.job.title, self.job.status), ('Senior Cashier', 'pending'))

    def test_invalid_job_post_shows_errors_instead_of_crashing(self):
        self.client.force_login(self.company_user)
        response = self.client.post(reverse('job-post'), {
            'title': 'Clerk', 'description': 'd', 'qualifications': 'q', 'location': 'x',
            'job_type': 'Full Time', 'vacancies': '1', 'deadline': 'not-a-date', 'salary': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid application deadline.')
        self.assertContains(response, 'Choose a valid employment type.')
        self.assertFalse(JobPost.objects.filter(title='Clerk').exists())
