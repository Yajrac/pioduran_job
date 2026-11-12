import re
import unicodedata
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def employer_field_errors(data):
    from user.models import User
    from employer.models import Employer
    errors = {}
    for field, label in [('company_name', 'Company name'), ('business_permit_no', 'Business permit number')]:
        if not data.get(field, '').strip():
            errors[field] = f'{label} is required.'
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
    for field, label in [('company_name', 'Company name'), ('business_permit_no', 'Business permit number'), ('contact_no', 'Mobile number')]:
        value = data.get(field, '').strip()
        if value and Employer.objects.filter(**{field + '__iexact': value}).exists():
            errors[field] = f'{label} is already registered.'
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
