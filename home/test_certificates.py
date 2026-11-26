from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from user.models import User
from applicant.models import Applicant, ApplicantCertificate
from employer.models import Employer, JobPost, JobApplication


class CertificateTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.field = ApplicantCertificate._meta.get_field('file')
        original = self.field.storage
        self.field.storage = FileSystemStorage(location=self.directory.name)
        self.addCleanup(setattr, self.field, 'storage', original)
        self.addCleanup(self.directory.cleanup)
        self.user = User.objects.create_user(username='candidate', role='applicant')
        self.applicant = Applicant.objects.create(user=self.user, first_name='Test', last_name='Applicant', email='test@example.com')
        self.employer_user = User.objects.create_user(username='company', role='employer')
        self.employer = Employer.objects.create(employer=self.employer_user, company_name='Company', business_permit_no='TEST', contact_no='09123456789')
        self.client.force_login(self.user)

    def image(self):
        stream = BytesIO()
        Image.new('RGB', (20, 20)).save(stream, format='PNG')
        return SimpleUploadedFile('certificate.png', stream.getvalue(), content_type='image/png')

    def upload(self):
        response = self.client.post(reverse('applicant-certificates'), {'title': 'Food Safety Training', 'file': self.image()})
        self.assertRedirects(response, reverse('applicant-certificates'))
        return ApplicantCertificate.objects.get()

    def test_upload_and_owner_access(self):
        certificate = self.upload()
        response = self.client.get(reverse('certificate-file', args=[certificate.pk]))
        self.assertEqual(response.status_code, 200)
        # View only: an HTML viewer page with the image inside, never the file itself
        self.assertTrue(response['Content-Type'].startswith('text/html'))
        self.assertNotIn('Content-Disposition', response)
        self.assertContains(response, 'data:image/png;base64,')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_employer_access_requires_application(self):
        certificate = self.upload()
        self.client.force_login(self.employer_user)
        url = reverse('certificate-file', args=[certificate.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        job = JobPost.objects.create(employer=self.employer, title='Helper', deadline=date(2030, 1, 1))
        JobApplication.objects.create(job=job, applicant=self.applicant)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.post(reverse('delete-certificate', args=[certificate.pk])).status_code, 404)

    def test_other_applicant_cannot_read_or_delete(self):
        certificate = self.upload()
        stranger = User.objects.create_user(username='stranger', role='applicant')
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse('certificate-file', args=[certificate.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete-certificate', args=[certificate.pk])).status_code, 404)

    def test_owner_delete_requires_post_and_removes_file(self):
        certificate = self.upload()
        name, storage = certificate.file.name, certificate.file.storage
        url = reverse('delete-certificate', args=[certificate.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(ApplicantCertificate.objects.exists())
        self.assertFalse(storage.exists(name))

    def test_fake_image_is_not_saved(self):
        response = self.client.post(reverse('applicant-certificates'), {'title': 'Invalid', 'file': SimpleUploadedFile('fake.png', b'not an image')})
        self.assertContains(response, 'This file could not be read')
        self.assertFalse(ApplicantCertificate.objects.exists())
