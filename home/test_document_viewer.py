import io
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from applicant.models import Applicant
from home.resume_validation import inspect_resume
from user.models import User

MEDIA = tempfile.mkdtemp()


def make_docx(text):
    """A minimal .docx with one paragraph."""
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml', f'<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class DocumentViewerTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('maria', 'm@example.com', 'x', role='applicant')
        self.applicant = Applicant.objects.create(user=self.user, first_name='Maria', last_name='Cruz',
                                                  middle_name='', email='m@example.com', phone_number='09171234567')
        self.client.force_login(self.user)

    def view(self):
        return self.client.get(reverse('my-document', args=['resume']))

    def test_pdf_is_shown_in_the_viewer_not_downloaded(self):
        self.applicant.resume.save('cv.pdf', ContentFile(b'%PDF-1.4 sample'))
        response = self.view()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/html'))
        self.assertNotIn('Content-Disposition', response)
        self.assertContains(response, 'id="pdfData"')
        self.assertContains(response, 'View only')
        self.assertNotContains(response, 'Download')

    def test_docx_is_previewed_in_a_sandboxed_frame(self):
        self.applicant.resume.save('cv.docx', ContentFile(make_docx('Customer service experience')))
        response = self.view()
        self.assertContains(response, 'sandbox')
        self.assertContains(response, 'Customer service experience')

    def test_old_doc_cannot_be_previewed_and_offers_a_new_upload(self):
        self.applicant.resume.save('cv.doc', ContentFile(b'old word file'))
        response = self.view()
        self.assertContains(response, "can't be previewed")
        self.assertContains(response, reverse('edit-applicant-profile'))

    def test_new_uploads_accept_only_pdf_and_docx(self):
        upload = io.BytesIO(b'x' * 200)
        upload.name, upload.size = 'cv.doc', 200
        self.assertTrue(inspect_resume(upload)['error'])

    def test_owner_sees_change_file_to_the_right_field(self):
        self.applicant.resume.save('cv.pdf', ContentFile(b'%PDF-1.4 sample'))
        response = self.view()
        self.assertContains(response, 'Change file')
        self.assertContains(response, reverse('edit-applicant-profile') + '#resume')

    def test_employer_does_not_see_change_file(self):
        from employer.models import Employer, JobApplication, JobPost
        from datetime import date
        self.applicant.resume.save('cv.pdf', ContentFile(b'%PDF-1.4 sample'))
        owner = User.objects.create_user('store', 's@example.com', 'x', role='employer')
        employer = Employer.objects.create(employer=owner, company_name='Store', business_permit_no='BP-1',
                                           contact_no='09170000001', description='d')
        job = JobPost.objects.create(employer=employer, title='Clerk', deadline=date(2030, 1, 1), status='approved')
        application = JobApplication.objects.create(job=job, applicant=self.applicant)
        self.client.force_login(owner)
        response = self.client.get(reverse('application-document', args=[application.pk, 'resume']))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Change file')
