"""Test helpers for employer registration with an uploaded business permit."""
from tempfile import TemporaryDirectory

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile

from employer.models import Employer, EmployerRegistrationOTP

PDF_BYTES = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def permit_upload(name='permit.pdf', content=PDF_BYTES, content_type='application/pdf'):
    return SimpleUploadedFile(name, content, content_type=content_type)


def registration_form(**changes):
    data = {
        'username': 'newcompany', 'email': 'hr@newcompany.example', 'password': 'Strong#2026', 'confirm_password': 'Strong#2026',
        'company_name': 'New Company', 'contact_no': '09171234567',
        'description': 'We sell general merchandise in Pio Duran.', 'business_permit_file': permit_upload(),
    }
    data.update(changes)
    return {key: value for key, value in data.items() if value is not None}


class TempPermitStorageMixin:
    """Keeps uploaded permits in a temporary folder instead of private_uploads/."""

    def setUp(self):
        super().setUp()
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for model in (Employer, EmployerRegistrationOTP):
            field = model._meta.get_field('business_permit_file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = FileSystemStorage(location=directory.name)
