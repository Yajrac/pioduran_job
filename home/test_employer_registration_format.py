from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from employer.models import Employer, EmployerRegistrationOTP
from user.models import User
from .permit_test_utils import TempPermitStorageMixin, permit_upload, registration_form
from .registration_validation import company_name_error, employer_username_error


def png_bytes():
    stream = BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(stream, 'PNG')
    return stream.getvalue()


@override_settings(DEBUG=True, OTP_DEV_MODE=True)
class EmployerRegistrationFormatTests(TempPermitStorageMixin, TestCase):
    url = reverse('employee-registration')

    def register(self, **changes):
        return self.client.post(self.url, registration_form(**changes))

    def test_valid_registration_keeps_permit_through_verification(self):
        self.register()
        registration = EmployerRegistrationOTP.objects.get(username='newcompany')
        self.assertTrue(registration.business_permit_file.name.startswith('business_permits/'))
        self.client.post(reverse('verify-employer-registration'), {'otp': registration.otp_code})
        employer = Employer.objects.get(company_name='New Company')
        self.assertEqual(employer.business_permit_file.name, registration.business_permit_file.name)
        self.assertEqual(employer.business_permit_no, '')
        self.assertEqual(employer.approval_status, 'pending')

    def test_company_name_spaces_are_tidied(self):
        self.register(company_name='  Rawis   General  Merchandise ')
        self.assertEqual(EmployerRegistrationOTP.objects.get().company_name, 'Rawis General Merchandise')

    def test_bad_formats_are_rejected(self):
        cases = {
            'username': ({'username': 'ab'}, 'Use 4 to 30 characters'),
            'username start': ({'username': '1company'}, 'Use 4 to 30 characters'),
            'company symbols': ({'company_name': 'Shop<>!'}, 'Use letters, numbers'),
            'company digits only': ({'company_name': '12345'}, 'must contain letters'),
            'short description': ({'description': 'Shop'}, 'at least 20 characters'),
            'no permit': ({'business_permit_file': None}, 'Upload your business permit.'),
            'permit type': ({'business_permit_file': permit_upload('permit.docx', b'PK..', 'application/msword')}, 'PDF, JPG or PNG'),
            'fake pdf': ({'business_permit_file': permit_upload('permit.pdf', b'not a pdf')}, 'could not be read'),
            'big permit': ({'business_permit_file': permit_upload('permit.pdf', b'%PDF-' + b'0' * (5 * 1024 * 1024))}, 'must not exceed 5 MB'),
            'fake logo': ({'company_logo': SimpleUploadedFile('logo.png', b'not an image', 'image/png')}, 'PNG, JPEG, or WebP'),
        }
        for label, (changes, message) in cases.items():
            with self.subTest(label):
                response = self.register(**changes)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
                self.assertFalse(EmployerRegistrationOTP.objects.exists())

    def test_image_permit_and_logo_are_accepted(self):
        self.register(business_permit_file=permit_upload('permit.png', png_bytes(), 'image/png'),
                      company_logo=SimpleUploadedFile('logo.png', png_bytes(), 'image/png'))
        self.assertTrue(EmployerRegistrationOTP.objects.get().business_permit_file.name.endswith('.png'))

    def test_format_helpers(self):
        self.assertEqual(employer_username_error('rawis_store.1'), '')
        self.assertEqual(company_name_error("J&B Trading Co. (Pio Duran)"), '')
        self.assertEqual(company_name_error('Peñafrancia Bakery'), '')

    def test_employer_username_check_applies_format(self):
        url = reverse('check-registration-username')
        self.assertIn('Use 4 to 30', self.client.get(url, {'username': 'ab', 'role': 'employer'}).json()['error'])
        self.assertEqual(self.client.get(url, {'username': 'goodname', 'role': 'employer'}).json()['error'], '')


class BusinessPermitAccessTests(TempPermitStorageMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_user(username='owner', role='employer')
        self.employer = Employer.objects.create(employer=self.owner, company_name='Rawis Store', contact_no='09170000001',
                                                description='General merchandise store.', business_permit_file=permit_upload())
        self.url = reverse('business-permit', args=[self.employer.pk])

    def test_admin_and_owner_can_open_permit(self):
        admin = User.objects.create_user(username='pesoadmin', role='admin')
        for user in [admin, self.owner]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/pdf')
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                response.close()

    def test_others_cannot_open_permit(self):
        other = User.objects.create_user(username='other', role='employer')
        applicant = User.objects.create_user(username='juan', role='applicant')
        for user in [other, applicant]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_permit_is_not_a_public_media_file(self):
        from pathlib import Path
        from django.conf import settings
        from employer.permit_storage import permit_storage
        location = Path(permit_storage().location).resolve()
        self.assertEqual(location, (settings.BASE_DIR / 'private_uploads').resolve())
        self.assertNotIn(Path(settings.MEDIA_ROOT).resolve(), [location, *location.parents])

    def test_public_company_page_hides_permit(self):
        self.client.force_login(User.objects.create_user(username='juan', role='applicant'))
        response = self.client.get(reverse('company_profile', args=[self.employer.pk]))
        self.assertNotContains(response, self.url)
        self.assertNotContains(response, 'Business Permit')

    def test_admin_detail_links_upload_and_shows_old_number(self):
        old_user = User.objects.create_user(username='oldco', role='employer')
        old = Employer.objects.create(employer=old_user, company_name='Old Co', contact_no='09170000002',
                                      description='Registered before uploads.', business_permit_no='BP-2025-001')
        self.client.force_login(User.objects.create_user(username='pesoadmin', role='admin'))
        self.assertContains(self.client.get(reverse('employer_detail', args=[self.employer.pk])), self.url)
        self.assertContains(self.client.get(reverse('employer_detail', args=[old.pk])), 'BP-2025-001')

    def test_owner_can_replace_permit_on_profile(self):
        self.client.force_login(self.owner)
        self.owner.email = 'owner@example.com'
        self.owner.save()
        old_name = self.employer.business_permit_file.name
        response = self.client.post(reverse('edit-employer-company-profile'), {
            'company_name': 'Rawis Store', 'contact_no': '09170000001', 'email': 'owner@example.com',
            'description': 'General merchandise store.', 'business_permit_file': permit_upload('new.pdf'),
        })
        self.assertRedirects(response, reverse('employer-company-profile'))
        self.employer.refresh_from_db()
        self.assertNotEqual(self.employer.business_permit_file.name, old_name)
