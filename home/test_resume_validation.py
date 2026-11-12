from io import BytesIO
from zipfile import ZipFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from reportlab.pdfgen import canvas
from .resume_validation import inspect_resume, NOT_RESUME


class ResumeValidationTests(SimpleTestCase):
    def pdf(self, text):
        output = BytesIO()
        document = canvas.Canvas(output)
        document.drawString(30, 700, text)
        document.save()
        return SimpleUploadedFile('resume.pdf', output.getvalue(), content_type='application/pdf')

    def test_fresh_graduate_resume_does_not_need_employment_history(self):
        upload = self.pdf('Education: Pio Duran Senior High School graduate. Skills: customer service, sales, communication. Email: example@example.com')
        self.assertEqual(inspect_resume(upload)['error'], '')
        self.assertEqual(upload.tell(), 0)

    def test_non_resume_document_is_rejected(self):
        upload = self.pdf('OFFICIAL RECEIPT Invoice number 1234. Payment received for water delivery, ten containers. Total amount due 500 pesos. Thank you for your purchase.')
        self.assertEqual(inspect_resume(upload)['error'], NOT_RESUME)

    def test_unreadable_file_is_warning_not_content_rejection(self):
        result = inspect_resume(SimpleUploadedFile('scan.pdf', b'not readable'))
        self.assertFalse(result['error'])
        self.assertTrue(result['warning'])

    def test_docx_is_checked_and_rewound(self):
        output = BytesIO()
        with ZipFile(output, 'w') as archive:
            archive.writestr('word/document.xml', '<document><p>Education: senior high school graduate. Skills: cooking and customer service. Contact: example@example.com, Pio Duran Albay.</p></document>')
        upload = SimpleUploadedFile('resume.docx', output.getvalue())
        self.assertFalse(inspect_resume(upload)['error'])
        self.assertEqual(upload.tell(), 0)

    def test_wrong_type_and_large_upload(self):
        self.assertEqual(inspect_resume(SimpleUploadedFile('photo.png', b'image'))['error'], NOT_RESUME)
        upload = SimpleUploadedFile('resume.pdf', b'')
        upload.size = 6 * 1024 * 1024
        self.assertTrue(inspect_resume(upload)['error'])
