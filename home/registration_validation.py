import re
import unicodedata
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


MAX_UPLOAD = 5 * 1024 * 1024
COMPANY_NAME_EXTRA = set(" .,&'()-/")


def employer_username_error(username):
    """Format only; availability is checked separately."""
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9._]{3,29}', username or ''):
        return 'Use 4 to 30 characters: start with a letter, then letters, numbers, dots or underscores.'
    return ''


def clean_company_name(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def company_name_error(value):
    value = clean_company_name(value)
    if not value:
        return 'Company name is required.'
    if not 2 <= len(value) <= 150:
        return 'Company name must be 2 to 150 characters.'
    if not any(c.isalpha() for c in value):
        return 'Company name must contain letters.'
    if any(not (c.isalnum() or c in COMPANY_NAME_EXTRA) for c in value):
        return "Use letters, numbers, spaces and . , & ' - ( ) / only."
    return ''


def description_error(value):
    length = len((value or '').strip())
    if length < 20:
        return 'Describe your company in at least 20 characters.'
    if length > 1000:
        return 'Keep the description to 1000 characters or fewer.'
    return ''


def _is_image(upload, formats):
    from PIL import Image
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            ok = image.format in formats
            image.verify()
        return ok
    except Exception:
        return False
    finally:
        upload.seek(0)


def logo_error(upload):
    """Optional company logo: a real PNG, JPEG or WebP image up to 5 MB."""
    if not upload:
        return ''
    if upload.size > MAX_UPLOAD:
        return 'Logo must not exceed 5 MB.'
    if not _is_image(upload, {'PNG', 'JPEG', 'WEBP'}):
        return 'Upload a PNG, JPEG, or WebP image.'
    return ''


def permit_file_error(upload, required=True):
    """Business permit: a real PDF, JPG or PNG file up to 5 MB."""
    if not upload:
        return 'Upload your business permit.' if required else ''
    extension = (upload.name or '').rsplit('.', 1)[-1].lower()
    if extension not in {'pdf', 'jpg', 'jpeg', 'png'}:
        return 'Upload the permit as a PDF, JPG or PNG file.'
    if upload.size > MAX_UPLOAD:
        return 'Business permit must not exceed 5 MB.'
    if extension == 'pdf':
        upload.seek(0)
        valid = upload.read(5) == b'%PDF-'
        upload.seek(0)
    else:
        valid = _is_image(upload, {'PNG', 'JPEG'})
    return '' if valid else 'This file could not be read. Upload a clear PDF, JPG or PNG of your permit.'


def employer_field_errors(data, files=None):
    from user.models import User
    from employer.models import Employer
    errors = {}
    files = files or {}
    checks = {
        'username': employer_username_error(data.get('username', '').strip()),
        'company_name': company_name_error(data.get('company_name', '')),
        'business_permit_file': permit_file_error(files.get('business_permit_file')),
        'description': description_error(data.get('description', '')),
        'company_logo': logo_error(files.get('company_logo')),
    }
    errors.update({field: error for field, error in checks.items() if error})
    email = data.get('email', '').strip()
    try:
        validate_email(email)
    except ValidationError:
        errors['email'] = 'Enter a valid email address.'
    if not re.fullmatch(r'09[0-9]{9}', data.get('contact_no', '').strip()):
        errors['contact_no'] = 'Enter an 11-digit mobile number starting with 09.'
    password = data.get('password', '')
    if not (len(password) >= 8 and re.search('[A-Z]', password) and re.search('[a-z]', password)
            and re.search('[0-9]', password) and re.search(r'[^A-Za-z0-9]', password)):
        errors['password'] = 'Password must meet all the listed security rules.'
    if not data.get('confirm_password') or password != data.get('confirm_password'):
        errors['confirm_password'] = 'Passwords do not match.'
    if email and User.objects.filter(email__iexact=email).exists():
        errors['email'] = 'Email address is already registered.'
    if email and 'email' not in errors:
        from .email_checks import email_domain_error
        domain_error = email_domain_error(email)
        if domain_error:
            errors['email'] = domain_error
    name = clean_company_name(data.get('company_name', ''))
    if 'company_name' not in errors and Employer.objects.filter(company_name__iexact=name).exists():
        errors['company_name'] = 'Company name is already registered.'
    contact = data.get('contact_no', '').strip()
    if contact and Employer.objects.filter(contact_no__iexact=contact).exists():
        errors['contact_no'] = 'Mobile number is already registered.'
    return errors


def applicant_field_errors(data):
    errors = {}
    for field, label in [('first_name', 'First name'), ('last_name', 'Last name'), ('middle_name', 'Middle name')]:
        value = data.get(field, '').strip()
        if not value:
            if field != 'middle_name':
                errors[field] = f'{label} is required.'
            continue
        if not any(c.isalpha() for c in value) or not all(
            c.isalpha() or unicodedata.category(c).startswith('M') or c in " .'-’"
            for c in value
        ):
            errors[field] = 'Use letters, spaces, apostrophes, hyphens or periods only. Numbers are not allowed.'
    if not re.fullmatch(r'09[0-9]{9}', data.get('phone_number', '').strip()):
        errors['phone_number'] = 'Enter an 11-digit mobile number starting with 09.'
    skills = [re.sub(r'\s+', ' ', item).strip() for item in data.get('skills', '').split(',') if item.strip()]
    if not skills:
        errors['skills'] = 'Add at least one skill.'
    elif len(skills) > 20:
        errors['skills'] = 'Add up to 20 skills.'
    elif any(len(skill) > 60 or not any(c.isalpha() for c in skill) for skill in skills):
        errors['skills'] = 'Each skill must contain a letter and be 60 characters or fewer.'
    elif len({skill.casefold() for skill in skills}) != len(skills):
        errors['skills'] = 'Remove duplicate skills.'
    return errors
