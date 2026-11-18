import re
from django.views.decorators.http import require_POST
from .resume_validation import inspect_resume
from .candidate_ranking import parse_required_skills, ranking_requirements_error, candidate_match

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from user.models import User
from employer.models import Employer, JobPost, JobApplication, EmployerRegistrationOTP
from applicant.models import Applicant, ApplicantRegistrationOTP
from .registration_validation import applicant_field_errors, employer_field_errors
from .login_limits import limited_login
from .company_forms import CompanyProfileForm
from employer.application_status import change_application_status
from django.http import JsonResponse
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError


def registration_company_check(request):
    fields = {"company_name": "Company name", "business_permit_no": "Business permit number", "contact_no": "Mobile number"}
    field = request.GET.get("field", "")
    value = request.GET.get("value", "").strip()
    if field not in fields:
        return JsonResponse({"error": "Invalid field."}, status=400)
    error = ""
    if not value:
        error = f"{fields[field]} is required."
    elif field == "contact_no" and not re.fullmatch(r"09[0-9]{9}", value):
        error = "Enter an 11-digit mobile number starting with 09."
    elif Employer.objects.filter(**{field + "__iexact": value}).exists():
        error = f"{fields[field]} is already registered."
    response = JsonResponse({"available": not bool(error), "error": error})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def resume_check(request):
    response = JsonResponse(inspect_resume(request.FILES.get("resume")))
    response["Cache-Control"] = "no-store"
    return response


def registration_username_check(request):
    username = request.GET.get('username', '').strip()
    error = username_error(username)
    response = JsonResponse({'available': not bool(error), 'error': error})
    response['Cache-Control'] = 'no-store'
    return response


def registration_email_check(request):
    from django.core.validators import validate_email
    email = request.GET.get('email', '').strip()
    error = ''
    try:
        validate_email(email)
    except ValidationError:
        error = 'Enter a valid email address.'
    if not error and (User.objects.filter(email__iexact=email).exists()
                      or Applicant.objects.filter(email__iexact=email).exists()):
        error = 'Email address is already registered.'
    from .email_checks import email_domain_error, suggest_email
    if not error:
        error = email_domain_error(email)
    response = JsonResponse({'available': not bool(error), 'error': error, 'suggestion': suggest_email(email)})
    response['Cache-Control'] = 'no-store'
    return response


OTP_MAX_ATTEMPTS = 5


def remember_demo_sms(request, phone, message, code):
    """Demo mode only (DEBUG + OTP_DEV_MODE): keep the 'sent' SMS so the
    verify page can show it on screen instead of a real text message."""
    from django.conf import settings
    if not (settings.DEBUG and getattr(settings, "OTP_DEV_MODE", False)):
        request.session.pop("demo_sms", None)
        return
    digits = re.sub(r"\D", "", phone or "")
    local = "0" + digits[2:] if digits.startswith("63") else digits
    masked = local[:4] + "•••" + local[-4:] if len(local) >= 8 else local
    request.session["demo_sms"] = {"to": masked, "message": message, "code": code}


def generate_otp():
    import secrets
    return f"{secrets.randbelow(900000) + 100000}"


def otp_attempts_exceeded(request, key):
    """Count a wrong OTP entry; True once the limit is reached."""
    attempts = request.session.get(key, 0) + 1
    request.session[key] = attempts
    return attempts >= OTP_MAX_ATTEMPTS


JOB_TYPES = {"full_time", "part_time", "contract", "internship", "temporary"}


def _category_other(data):
    """The typed category for "Other", tidied; blank for every other category."""
    if data.get("category") != "other":
        return ""
    return re.sub(r"\s+", " ", data.get("category_other", "")).strip()[:60]


def job_form_errors(data):
    """Validate the core job post fields; returns a list of messages."""
    errors = []
    for field, label in [("title", "Job title"), ("description", "Job description"),
                         ("qualifications", "Qualifications"), ("location", "Location")]:
        if not data.get(field, "").strip():
            errors.append(f"{label} is required.")
    if len(data.get("title", "").strip()) > 255 or len(data.get("location", "").strip()) > 255:
        errors.append("Job title and location must be at most 255 characters.")
    if data.get("job_type") not in JOB_TYPES:
        errors.append("Choose a valid employment type.")
    from employer.job_categories import CATEGORY_KEYS
    if data.get("category") not in CATEGORY_KEYS:
        errors.append("Choose a job category.")
    elif data.get("category") == "other":
        other = re.sub(r"\s+", " ", data.get("category_other", "")).strip()
        if not other:
            errors.append("Type the job category when you choose Other.")
        elif len(other) > 60 or not any(c.isalpha() for c in other):
            errors.append("The job category must contain letters and be at most 60 characters.")
    salary = data.get("salary", "").strip().replace(",", "")
    if salary:
        try:
            value = Decimal(salary)
            if not value.is_finite() or value < 0 or value >= Decimal("100000000"):
                raise InvalidOperation
        except InvalidOperation:
            errors.append("Salary must be a number from 0 to 99,999,999.99.")
    if (data.get("salary_period") or "month") not in {"month", "day", "hour"}:
        errors.append("Choose whether the salary is per month, per day, or per hour.")
    try:
        deadline = datetime.strptime(data.get("deadline", ""), "%Y-%m-%d").date()
        if deadline < timezone.localdate():
            errors.append("Application deadline cannot be in the past.")
    except ValueError:
        errors.append("Enter a valid application deadline.")
    return errors


def username_error(username):
    if not username or len(username) > 150:
        return 'Enter a username of 1 to 150 characters.'
    try:
        UnicodeUsernameValidator()(username)
    except ValidationError:
        return 'Use letters, numbers and @/./+/-/_ only.'
    if User.objects.filter(username__iexact=username).exists():
        return 'Username already exists. Please choose another username.'
    return ''
from django.contrib import messages
import re
from django.db.models import Count
from django.db.models.functions import TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
import csv
import io
import os
import shutil
from django.core.files import File
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.db import transaction
import random
from django.contrib.auth.hashers import make_password

from .sms import SMS_BRAND, send_sms, format_ph_mobile
from .landing import signed_in_users_go_home

def normalize_skill(skill):
    """
    Normalize a skill for matching.
    """
    return re.sub(r"\s+", " ", skill.strip().lower())


def skill_matches_text(skill, text):
    from .skill_extraction import skill_in_text
    return skill_in_text(skill, text)


def get_job_recommendation(job, applicant_skills):
    """
    Calculate how closely a job matches the applicant's skills.
    """

    if not applicant_skills:
        return 0, []

    # Combine all relevant job information
    job_text = " ".join([
        str(getattr(job, "title", "") or ""),
        str(getattr(job, "description", "") or ""),
        str(getattr(job, "qualifications", "") or ""),
        str(getattr(job, "responsibilities", "") or ""),
        str(getattr(job, "location", "") or ""),
    ])

    # Applicant skills can be separated by:
    # comma
    # semicolon
    # new line
    # |
    raw_skills = re.split(
        r"[,;\n|]+",
        applicant_skills
    )

    normalized_skills = []

    for raw_skill in raw_skills:

        skill = normalize_skill(raw_skill)

        if skill and skill not in normalized_skills:
            normalized_skills.append(skill)

    if not normalized_skills:
        return 0, []

    matched_skills = []

    for skill in normalized_skills:

        if skill_matches_text(
            skill,
            job_text
        ):
            matched_skills.append(skill)

    # Calculate percentage
    score = round(
        (
            len(matched_skills)
            / len(normalized_skills)
        ) * 100
    )

    return score, matched_skills


@signed_in_users_go_home(("GET", "HEAD"))
def home_view(request):

    # ==========================================
    # FEATURED JOBS
    # Most applicants first
    # ==========================================

    featured_jobs = (
        JobPost.objects.public()
        .annotate(
            application_count=Count("applications")
        )
        .order_by(
            "-application_count",
            "-created_at",
            "-pk"
        )[:6]
    )

    # ==========================================
    # PORTAL STATISTICS
    # ==========================================

    registered_applicants = Applicant.objects.count()

    active_job_vacancies = JobPost.objects.public().count()

    successful_placements = JobApplication.objects.filter(
        status__in=["accepted", "hired"]
    ).count()

    # ==========================================
    # RENDER HOME PAGE
    # ==========================================

    return render(
        request,
        "pages/home_view.html",
        {
            "featured_jobs": featured_jobs,
            "registered_applicants": registered_applicants,
            "active_job_vacancies": active_job_vacancies,
            "successful_placements": successful_placements,
        }
    )

@signed_in_users_go_home()
def employee_registration(request):

    if request.method == "POST":
        errors = employer_field_errors(request.POST)
        error = username_error(request.POST.get('username', '').strip())
        if error:
            errors['username'] = error
        if errors:
            return render(request, 'pages/register_employer.html', {
                'field_errors': errors, 'form_values': request.POST,
                'account_errors': any(key in errors for key in ['username', 'email', 'password', 'confirm_password']),
            })

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        company_name = request.POST.get(
            "company_name",
            ""
        ).strip()

        business_permit_no = request.POST.get(
            "business_permit_no",
            ""
        ).strip()

        contact_no = request.POST.get(
            "contact_no",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        company_logo = request.FILES.get(
            "company_logo"
        )

        # ==========================================
        # CHECK USERNAME
        # ==========================================

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # CHECK EMAIL
        # ==========================================

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email address is already registered.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # CHECK COMPANY
        # ==========================================

        if Employer.objects.filter(
            company_name=company_name
        ).exists():

            messages.error(
                request,
                "Company name is already registered.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # CHECK BUSINESS PERMIT
        # ==========================================

        if Employer.objects.filter(
            business_permit_no=business_permit_no
        ).exists():

            messages.error(
                request,
                "Business Permit Number already exists.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # CHECK CONTACT NUMBER
        # ==========================================

        if Employer.objects.filter(
            contact_no=contact_no
        ).exists():

            messages.error(
                request,
                "Contact number is already registered.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # FORMAT MOBILE NUMBER
        # ==========================================

        phone_number = format_ph_mobile(
            contact_no
        )

        # ==========================================
        # GENERATE OTP
        # ==========================================

        otp_code = generate_otp()

        # ==========================================
        # DELETE OLD PENDING REGISTRATION
        # ==========================================

        EmployerRegistrationOTP.objects.filter(
            email=email,
            is_verified=False
        ).delete()

        # ==========================================
        # CREATE TEMPORARY REGISTRATION
        # ==========================================

        registration = EmployerRegistrationOTP.objects.create(

            username=username,

            email=email,

            password=make_password(password),

            company_name=company_name,

            business_permit_no=business_permit_no,

            contact_no=contact_no,

            description=description,

            company_logo=company_logo,

            otp_code=otp_code,

            expires_at=timezone.now()
            + timedelta(minutes=5)
        )

        # ==========================================
        # SMS MESSAGE
        # ==========================================

        sms_message = (
            f"{SMS_BRAND}: Your employer registration "
            f"verification code is {otp_code}. "
            f"This code will expire in 5 minutes."
        )

        # ==========================================
        # SEND SMS
        # ==========================================

        try:

            response = send_sms(
                phone_number,
                sms_message
            )

            if not response.ok:

                registration.delete()

                messages.error(
                    request,
                    "Unable to send verification code. Please try again.",
                    extra_tags="registration"
                )

                return redirect(
                    "employee-registration"
                )

        except Exception as e:

            registration.delete()

            messages.error(
                request,
                "SMS service is currently unavailable. Please try again.",
                extra_tags="registration"
            )

            return redirect(
                "employee-registration"
            )

        # ==========================================
        # SAVE REGISTRATION ID IN SESSION
        # ==========================================

        request.session[
            "employer_registration_id"
        ] = registration.id
        request.session.pop("employer_otp_attempts", None)
        remember_demo_sms(request, contact_no, sms_message, otp_code)

        # ==========================================
        # GO TO OTP PAGE
        # ==========================================

        return redirect(
            "verify-employer-registration"
        )

    return render(
        request,
        "pages/register_employer.html"
    )


def verify_employer_registration(request):

    registration_id = request.session.get(
        "employer_registration_id"
    )

    # ==========================================
    # CHECK SESSION
    # ==========================================

    if not registration_id:

        messages.error(
            request,
            "Registration session expired. Please register again.",
            extra_tags="registration"
        )

        return redirect(
            "employee-registration"
        )

    # ==========================================
    # GET REGISTRATION
    # ==========================================

    try:

        registration = EmployerRegistrationOTP.objects.get(
            id=registration_id,
            is_verified=False
        )

    except EmployerRegistrationOTP.DoesNotExist:

        messages.error(
            request,
            "Registration request was not found.",
            extra_tags="registration"
        )

        return redirect(
            "employee-registration"
        )

    # ==========================================
    # CHECK OTP EXPIRATION
    # ==========================================

    if registration.is_expired():

        registration.delete()

        request.session.pop(
            "employer_registration_id",
            None
        )

        messages.error(
            request,
            "Verification code has expired. Please register again.",
            extra_tags="registration"
        )

        return redirect(
            "employee-registration"
        )

    # ==========================================
    # VERIFY OTP
    # ==========================================

    if request.method == "POST":

        otp = request.POST.get(
            "otp",
            ""
        ).strip()

        # ======================================
        # INVALID OTP
        # ======================================

        if otp != registration.otp_code:

            if otp_attempts_exceeded(request, "employer_otp_attempts"):
                registration.delete()
                request.session.pop("employer_registration_id", None)
                request.session.pop("employer_otp_attempts", None)
                messages.error(
                    request,
                    "Too many incorrect codes. Please register again.",
                    extra_tags="registration"
                )
                return redirect("employee-registration")

            messages.error(
                request,
                "Invalid verification code.",
                extra_tags="registration"
            )

            return render(
                request,
                "pages/verify_employer.html"
            )

        # ======================================
        # MARK VERIFIED
        # ======================================

        registration.is_verified = True

        registration.save()

        # ======================================
        # CREATE USER
        # ======================================

        # registration.password is already hashed.
        user = User(
            username=registration.username,
            email=registration.email,
            password=registration.password,
            role="employer"
        )
        user.save()

        # ======================================
        # CREATE EMPLOYER PROFILE
        # ======================================

        Employer.objects.create(
            employer=user,

            company_name=registration.company_name,

            business_permit_no=registration.business_permit_no,

            contact_no=registration.contact_no,

            description=registration.description,

            company_logo=registration.company_logo,
            approval_status="pending",
            is_active=False,
        )

        # ======================================
        # DELETE TEMPORARY REGISTRATION
        # ======================================

        registration.delete()

        # ======================================
        # CLEAR SESSION
        # ======================================

        request.session.pop(
            "employer_registration_id",
            None
        )

        # ======================================
        # SUCCESS
        # ======================================

        messages.success(
            request,
            "Registration verified. Log in to view your pending PESO approval status.",
            extra_tags="registration"
        )

        return redirect(
            "login-user"
        )

    return render(
        request,
        "pages/verify_employer.html"
    )

@signed_in_users_go_home()
def applicant_registration(request):

    if request.method == "POST":
        field_errors = applicant_field_errors(request.POST)
        resume_result = inspect_resume(request.FILES.get("resume"))
        if resume_result["error"]:
            field_errors["resume"] = resume_result["error"]
        account_error = username_error(request.POST.get('username', '').strip())
        if account_error:
            field_errors['username'] = account_error
        password_value = request.POST.get('password', '')
        if not (len(password_value) >= 8 and re.search(r'[A-Z]', password_value)
                and re.search(r'[a-z]', password_value) and re.search(r'[0-9]', password_value)
                and re.search(r'[^A-Za-z0-9]', password_value)):
            field_errors['password'] = 'Password must meet all the listed security rules.'
        if not request.POST.get('confirm_password') or password_value != request.POST.get('confirm_password'):
            field_errors['confirm_password'] = 'Passwords do not match.'
        if field_errors:
            return render(request, "pages/register_applicant.html", {
                "field_errors": field_errors,
                "account_errors": any(key in field_errors for key in ['username', 'password', 'confirm_password']),
                "form_values": request.POST,
            })

        # ==========================================
        # GET FORM DATA
        # ==========================================

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone_number = request.POST.get(
            "phone_number",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        middle_name = request.POST.get(
            "middle_name",
            ""
        ).strip()

        skills = request.POST.get(
            "skills",
            ""
        ).strip()

        resume = request.FILES.get(
            "resume"
        )

        cover_letter = request.FILES.get(
            "cover_letter"
        )

        # ==========================================
        # CHECK USERNAME
        # ==========================================

        if User.objects.filter(
            username=username
        ).exists():

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Username already exists. "
                        "Please choose another username."
                    )
                }
            )

        # ==========================================
        # CHECK USER EMAIL
        # ==========================================

        if email and User.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Email address is already registered. "
                        "Please use another email."
                    )
                }
            )

        # ==========================================
        # CHECK APPLICANT EMAIL
        # ==========================================

        if email and Applicant.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Email address is already registered. "
                        "Please use another email."
                    )
                }
            )

        # ==========================================
        # CHECK THAT THE EMAIL DOMAIN EXISTS
        # ==========================================

        from .email_checks import email_domain_error
        domain_error = email_domain_error(email) if email else ""
        if domain_error:
            return render(request, "pages/register_applicant.html", {"error": domain_error})

        # ==========================================
        # CHECK PHONE NUMBER
        # ==========================================

        if phone_number and Applicant.objects.filter(
            phone_number=phone_number
        ).exists():

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Phone number is already registered. "
                        "Please use another phone number."
                    )
                }
            )

        # ==========================================
        # VALIDATE PHONE NUMBER
        # ==========================================

        if not phone_number.startswith("09"):

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Please enter a valid Philippine "
                        "mobile number starting with 09."
                    )
                }
            )

        if len(phone_number) != 11:

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Mobile number must contain "
                        "11 digits."
                    )
                }
            )

        # ==========================================
        # VALIDATE SKILLS
        # ==========================================

        if not skills:

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Please enter at least one skill "
                        "to help us recommend suitable jobs."
                    )
                }
            )

        # ==========================================
        # FORMAT PHONE FOR SMS
        # ==========================================

        formatted_phone = format_ph_mobile(
            phone_number
        )

        # ==========================================
        # GENERATE OTP
        # ==========================================

        otp_code = generate_otp()

        # ==========================================
        # OTP EXPIRATION
        # 5 MINUTES
        # ==========================================

        expires_at = (
            timezone.now()
            + timedelta(minutes=5)
        )

        # ==========================================
        # DELETE OLD TEMPORARY REGISTRATION
        # ==========================================

        ApplicantRegistrationOTP.objects.filter(
            username=username
        ).delete()

        ApplicantRegistrationOTP.objects.filter(
            phone_number=phone_number
        ).delete()

        # ==========================================
        # HASH PASSWORD
        # ==========================================

        hashed_password = make_password(
            password
        )

        # ==========================================
        # CREATE TEMPORARY REGISTRATION
        # ==========================================

        registration = ApplicantRegistrationOTP.objects.create(

            username=username,

            email=email,

            phone_number=phone_number,

            first_name=first_name,

            last_name=last_name,

            middle_name=middle_name,

            skills=skills,

            password=hashed_password,

            resume=resume,

            cover_letter=cover_letter,

            otp_code=otp_code,

            expires_at=expires_at,
        )

        # ==========================================
        # SMS MESSAGE
        # ==========================================

        message = (
            f"{SMS_BRAND}: "
            f"Your verification code is {otp_code}. "
            "This code will expire in 5 minutes."
        )

        # ==========================================
        # SEND SMS
        # ==========================================

        try:

            response = send_sms(
                formatted_phone,
                message
            )

            # ======================================
            # CHECK SMS RESULT (details are logged)
            # ======================================

            if not response.ok:

                registration.delete()

                return render(
                    request,
                    "pages/register_applicant.html",
                    {
                        "error": (
                            "Unable to send verification "
                            "code. Please try again."
                        )
                    }
                )

        except Exception as e:

            registration.delete()

            return render(
                request,
                "pages/register_applicant.html",
                {
                    "error": (
                        "Unable to send verification "
                        "code. Please try again later."
                    )
                }
            )

        # ==========================================
        # SAVE REGISTRATION ID IN SESSION
        # ==========================================

        request.session[
            "applicant_registration_id"
        ] = registration.id
        request.session.pop("applicant_otp_attempts", None)
        remember_demo_sms(request, phone_number, message, otp_code)

        # ==========================================
        # REDIRECT TO OTP PAGE
        # ==========================================

        return redirect(
            "verify-applicant-registration"
        )

    # ==============================================
    # GET REQUEST
    # ==============================================

    return render(
        request,
        "pages/register_applicant.html"
    )

def verify_applicant_registration(request):

    # ==========================================
    # GET REGISTRATION ID FROM SESSION
    # ==========================================

    registration_id = request.session.get(
        "applicant_registration_id"
    )

    if not registration_id:
        return redirect("applicant-registration")

    # ==========================================
    # GET TEMPORARY REGISTRATION
    # ==========================================

    try:
        registration = ApplicantRegistrationOTP.objects.get(
            id=registration_id
        )

    except ApplicantRegistrationOTP.DoesNotExist:
        request.session.pop(
            "applicant_registration_id",
            None
        )
        return redirect("applicant-registration")

    # ==========================================
    # CHECK EXPIRATION
    # ==========================================

    if registration.is_expired():
        registration.delete()

        request.session.pop(
            "applicant_registration_id",
            None
        )

        return render(
            request,
            "pages/verify_applicant.html",
            {
                "error": (
                    "Your verification code has expired. "
                    "Please register again."
                )
            }
        )

    # ==========================================
    # VERIFY OTP
    # ==========================================

    if request.method == "POST":

        otp = request.POST.get(
            "otp",
            ""
        ).strip()

        if otp != registration.otp_code:
            if otp_attempts_exceeded(request, "applicant_otp_attempts"):
                registration.delete()
                request.session.pop("applicant_registration_id", None)
                request.session.pop("applicant_otp_attempts", None)
                return render(
                    request,
                    "pages/verify_applicant.html",
                    {"error": "Too many incorrect codes. Please register again."}
                )
            return render(
                request,
                "pages/verify_applicant.html",
                {
                    "error": (
                        "Invalid verification code. "
                        "Please try again."
                    )
                }
            )

        # ==========================================
        # VALIDATE SAVED SKILLS
        # ==========================================

        skills = (registration.skills or "").strip()

        if not skills:
            return render(
                request,
                "pages/verify_applicant.html",
                {
                    "error": (
                        "Your skills were not saved during "
                        "registration. Please register again."
                    )
                }
            )

        # ==========================================
        # CREATE USER AND APPLICANT ATOMICALLY
        # ==========================================

        try:
            with transaction.atomic():

                # Prevent duplicate account creation.
                if User.objects.filter(
                    username=registration.username
                ).exists():
                    return render(
                        request,
                        "pages/verify_applicant.html",
                        {
                            "error": (
                                "This username is already registered. "
                                "Please contact support."
                            )
                        }
                    )

                if User.objects.filter(
                    email=registration.email
                ).exists():
                    return render(
                        request,
                        "pages/verify_applicant.html",
                        {
                            "error": (
                                "This email is already registered. "
                                "Please contact support."
                            )
                        }
                    )

                # Create the user.
                user = User(
                    username=registration.username,
                    email=registration.email,
                    password=registration.password,
                )

                user.role = "applicant"
                user.save()

                # Create the permanent applicant profile.
                Applicant.objects.create(
                    user=user,
                    first_name=registration.first_name,
                    last_name=registration.last_name,
                    middle_name=registration.middle_name,
                    email=registration.email,
                    phone_number=registration.phone_number,

                    # IMPORTANT: copy skills from the OTP record.
                    skills=skills,

                    resume=registration.resume,
                    cover_letter=registration.cover_letter,
                )

                # Mark the temporary record as verified.
                registration.is_verified = True
                registration.save(
                    update_fields=["is_verified"]
                )

                # Delete the temporary registration.
                registration.delete()

        except Exception:
            # Log the actual exception in your server logs
            # when diagnosing unexpected database failures.
            raise

        # ==========================================
        # CLEAR SESSION
        # ==========================================

        request.session.pop(
            "applicant_registration_id",
            None
        )

        # ==========================================
        # REDIRECT TO LOGIN
        # ==========================================

        return redirect("login-user")

    # ==========================================
    # DISPLAY OTP PAGE
    # ==========================================

    return render(
        request,
        "pages/verify_applicant.html"
    )


@limited_login
@signed_in_users_go_home(("GET", "HEAD"))
def login_user(request):
    if request.method == "POST":
        username=request.POST.get('username')
        password=request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.role not in ('applicant', 'employer'):
                error = 'Invalid username or password.'
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': error, 'clear_fields': ['username', 'password']}, status=400)
                return render(request, 'pages/login.html', {
                    'login_notice': error, 'login_username': '',
                })
            login(request, user)
            request._public_login_success = True

            if user.role == "employer":
                target = 'employer-dashboard'
            elif user.role == "applicant":
                target = 'applicant-profile'
            else:
                target = 'login-user'
            if request.headers.get('Accept') == 'application/json':
                from django.urls import reverse
                return JsonResponse({'redirect': reverse(target)})
            return redirect(target)
        exists = User.objects.filter(username=username).exists()
        field = 'password' if exists else 'username'
        error = 'Wrong password.' if exists else 'Username not found.'
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'field': field, 'error': error}, status=400)
        return render(request, 'pages/login.html', {
            'login_error_field': field, 'login_error': error,
            'login_username': username if exists else '',
        })
    return render(request, 'pages/login.html')

def logout_user(request):
    logout(request)
    return redirect('login-user')

def _employer_dashboard_extras(employer, jobs, applications, now):
    """Pipeline counts, last-6-months series and open jobs for the overview page."""
    by_status = dict(applications.order_by().values_list("status").annotate(n=Count("pk")))
    pipeline = [(label, by_status.get(key, 0), key) for key, label in [
        ("pending", "Pending"), ("reviewing", "Reviewing"), ("shortlisted", "Shortlisted"),
        ("offered", "Offered"), ("hired", "Hired"), ("rejected", "Rejected")]]
    pipeline_top = max([count for _, count, _ in pipeline] + [1])

    month_start = timezone.localdate().replace(day=1)
    months = []
    for back in range(5, -1, -1):
        year, month = month_start.year, month_start.month - back
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))
    counts = {(item["month"].year, item["month"].month): item["total"] for item in
              applications.order_by().annotate(month=TruncMonth("applied_at")).values("month").annotate(total=Count("pk"))
              if item["month"]}
    import datetime as _dt
    series = [{"label": _dt.date(y, m, 1).strftime("%b"), "total": counts.get((y, m), 0)} for y, m in months]
    series_top = max([item["total"] for item in series] + [1])
    for item in series:
        item["percent"] = round(item["total"] / series_top * 100)

    open_jobs = (jobs.filter(status="approved", deadline__gte=timezone.localdate())
                 .annotate(application_count=Count("applications")).order_by("deadline")[:5])
    return {
        "hired": by_status.get("hired", 0),
        "awaiting": by_status.get("pending", 0) + by_status.get("reviewing", 0),
        "pending_jobs": jobs.filter(status="pending").count(),
        "pipeline": [{"label": label, "count": count, "key": key, "percent": round(count / pipeline_top * 100)}
                     for label, count, key in pipeline],
        "month_series": series,
        "month_series_total": sum(item["total"] for item in series),
        "open_jobs": open_jobs,
    }


@login_required(login_url="login-user")
def employer_dashboard(request):
    employer = request.user.employer

    jobs = JobPost.objects.filter(employer=employer)

    applications = JobApplication.objects.filter(
        job__employer=employer
    ).select_related(
        "job",
        "applicant",
        "applicant__user"
    ).order_by("-applied_at")

    # -------------------------
    # Weekly Statistics
    # -------------------------
    today = timezone.now()

    this_week = applications.filter(
        applied_at__gte=today - timedelta(days=7)
    ).count()

    last_week = applications.filter(
        applied_at__gte=today - timedelta(days=14),
        applied_at__lt=today - timedelta(days=7)
    ).count()

    max_week = max(this_week, last_week, 1)

    this_week_percent = int((this_week / max_week) * 100)
    last_week_percent = int((last_week / max_week) * 100)

    # -------------------------
    # Monthly Statistics
    # -------------------------
    monthly = (
        applications
        .annotate(month=TruncMonth("applied_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    from employer.hiring_analytics import hiring_analytics
    hires = list(applications.filter(status='hired').select_related('job__employer'))
    hiring_stats = hiring_analytics(hires)

    context = {
        'hiring_stats':hiring_stats,

        "employer": employer,

        "total_jobs": jobs.count(),
        "published_jobs": jobs.filter(status='approved').count(),
        "total_applications": applications.count(),

        "pending_review": applications.filter(status="pending").count(),
        "reviewing": applications.filter(status="reviewing").count(),
        "shortlisted": applications.filter(status="shortlisted").count(),
        "accepted": applications.filter(status__in=["accepted", "hired"]).count(),
        "rejected": applications.filter(status="rejected").count(),

        "recent_applications": applications[:5],

        # Weekly
        "this_week": this_week,
        "last_week": last_week,
        "this_week_percent": this_week_percent,
        "last_week_percent": last_week_percent,

        # Monthly
        "monthly": monthly,
    }
    context.update(_employer_dashboard_extras(employer, jobs, applications, today))

    return render(
        request,
        "pages/employer-dashboard.html",
        context
    )

# @login_required(login_url="login-user")
def browse_job(request):
    applied_job_ids = set()
    if request.user.is_authenticated and request.user.role == 'applicant':
        applied_job_ids = set(JobApplication.objects.filter(
            applicant__user=request.user
        ).values_list('job_id', flat=True))

    # =========================================================
    # APPROVED JOBS
    # =========================================================

    job = list(JobPost.objects.public().select_related("employer").order_by("-created_at"))

    # Filter options with counts, and days left before each deadline
    from collections import Counter
    today = timezone.localdate()
    for item in job:
        item.days_left = (item.deadline - today).days if item.deadline else None
    category_counts = Counter((j.category, j.get_category_display()) for j in job)
    type_counts = Counter((j.job_type, j.get_job_type_display()) for j in job)
    employer_counts = Counter(j.employer.company_name for j in job)
    browse_filters = {
        "categories": sorted(category_counts.items(), key=lambda item: (-item[1], item[0][1])),
        "types": sorted(type_counts.items(), key=lambda item: (-item[1], item[0][1])),
        "employers": sorted(employer_counts.items(), key=lambda item: item[0].casefold()),
    }


    # =========================================================
    # DEFAULT RECOMMENDATIONS
    # =========================================================

    recommended_jobs = []


    # =========================================================
    # GET APPLICANT PROFILE
    # =========================================================

    applicant = getattr(
        request.user,
        "applicant_profile",
        None
    )


    # =========================================================
    # SKILL-BASED RECOMMENDATIONS
    # =========================================================

    from .skill_extraction import experience_matches
    experiences = list(applicant.work_experiences.all()) if applicant else []
    if applicant and (applicant.skills or experiences):

        for current_job in job:

            score, matched_skills = (
                get_job_recommendation(
                    current_job,
                    applicant.skills
                )
            )

            matched_experience = experience_matches(current_job, experiences)
            if experiences:
                # Relevant experience contributes 20%; skill overlap contributes 80%.
                score = round(score * 0.8 + (20 if matched_experience else 0))

            # Only recommend jobs with
            # at least one matching skill
            if score > 0:

                recommended_jobs.append({
                    "job": current_job,
                    "score": score,
                    "matched_skills": matched_skills,
                    "matched_experience": matched_experience,
                })


        # Highest matching jobs first
        recommended_jobs.sort(
            key=lambda item: (
                item["score"],
                item["job"].created_at
            ),
            reverse=True
        )


        # Show only the top 5 recommendations
        recommended_jobs = recommended_jobs[:5]


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "pages/browse_job.html",
        {
            "job": job,
            "recommended_jobs": recommended_jobs,
            "applied_job_ids": applied_job_ids,
            "browse_filters": browse_filters,
        }
    )

@login_required(login_url="login-user")
def job_list(request):
    employer = request.user.employer

    jobs = JobPost.objects.filter(
        employer=employer
    ).order_by("-created_at")

    return render(request, "pages/job_list.html", {
        "jobs": jobs
    })

@login_required(login_url="login-user")
def post_job(request):
    employer = get_object_or_404(
        Employer,
        employer=request.user
    )

    if request.method == "POST":
        ranking_error = ranking_requirements_error(request.POST.get('required_skills', ''))
        if ranking_error:
            return render(request, 'components/job_post_form.html', { 'form_values':request.POST, 'ranking_error':ranking_error})

        raw_vacancies = request.POST.get('vacancies', '')
        if not re.fullmatch(r'[0-9]+', raw_vacancies) or not 1 <= int(raw_vacancies) <= 2147483647:
            return render(request, 'components/job_post_form.html', {
                'vacancies_error': 'Enter a whole number of vacancies, at least 1.',
                'form_values': request.POST,
            })

        job_errors = job_form_errors(request.POST)
        if job_errors:
            return render(request, 'components/job_post_form.html', {
                'form_values': request.POST, 'job_errors': job_errors,
            })

        salary = request.POST.get("salary", "").strip().replace(",", "")

        # Convert empty salary to None
        if not salary:
            salary = None

        JobPost.objects.create(
            employer=employer,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            required_skills=', '.join(parse_required_skills(request.POST.get('required_skills', ''))),
            experience_required=request.POST.get('experience_required') == 'on',
            qualifications=request.POST.get("qualifications"),
            responsibilities=request.POST.get("responsibilities", ""),
            salary=salary,
            salary_period=request.POST.get("salary_period") or "month",
            category_other=_category_other(request.POST),
            location=request.POST.get("location"),
            category=request.POST.get("category"),
            job_type=request.POST.get("job_type"),
            vacancies=request.POST.get("vacancies"),
            deadline=request.POST.get("deadline"),
        )

        messages.success(
            request,
            f"\u201c{request.POST.get('title', '').strip()}\u201d was submitted. It is waiting for PESO approval "
            "and will appear on Browse Jobs once approved.",
            extra_tags="job_saved",
        )
        return redirect("job-list")

    return render(
        request,
        "components/job_post_form.html"
    )

@login_required(login_url="login-user")
def update_job(request, id):
    employer = get_object_or_404(Employer, employer=request.user)

    job = get_object_or_404(
        JobPost,
        id=id,
        employer=employer
    )

    if request.method == "POST":
        ranking_error = ranking_requirements_error(request.POST.get('required_skills', ''))
        if ranking_error:
            return render(request, 'components/job_post_form.html', {'job': job, 'form_values':request.POST, 'ranking_error':ranking_error})

        raw_vacancies = request.POST.get('vacancies', '')
        if not re.fullmatch(r'[0-9]+', raw_vacancies) or not 1 <= int(raw_vacancies) <= 2147483647:
            return render(request, 'components/job_post_form.html', {
                'job': job, 'form_values': request.POST,
                'vacancies_error': 'Enter a whole number of vacancies, at least 1.',
            })
        job_errors = job_form_errors(request.POST)
        if job_errors:
            return render(request, 'components/job_post_form.html', {
                'job': job, 'form_values': request.POST, 'job_errors': job_errors,
            })
        job.required_skills = ', '.join(parse_required_skills(request.POST.get('required_skills', '')))
        job.experience_required = request.POST.get('experience_required') == 'on'
        job.title = request.POST.get("title")
        job.description = request.POST.get("description")
        job.qualifications = request.POST.get("qualifications")
        job.responsibilities = request.POST.get("responsibilities", "")
        job.salary = request.POST.get("salary", "").strip().replace(",", "") or None
        job.salary_period = request.POST.get("salary_period") or "month"
        job.category_other = _category_other(request.POST)
        job.location = request.POST.get("location")
        job.category = request.POST.get("category")
        job.job_type = request.POST.get("job_type")
        job.vacancies = request.POST.get("vacancies")
        job.deadline = request.POST.get("deadline")

        # Edited content must be reviewed again before it is public.
        was_published = job.status == "approved"
        if was_published:
            job.status = "pending"
            job.approved_at = None

        job.save()

        if was_published:
            messages.info(request, "Changes saved. The job is hidden until PESO approves it again.",
                          extra_tags="job_saved")
        else:
            messages.success(request, "Changes saved. The job is still waiting for PESO approval.",
                             extra_tags="job_saved")

        return redirect("job-list")

    return render(
        request,
        "components/job_post_form.html",
        {
            "job": job
        }
    )

@login_required(login_url="login-user")
def employer_delete_job(request, id):
    employer = get_object_or_404(Employer, employer=request.user)

    # Ensure the job belongs to the logged-in employer
    job = get_object_or_404(
        JobPost,
        id=id,
        employer=employer
    )

    if request.method == "POST":
        job.delete()
        return redirect("job-list")

    return render(request, "components/employer_delete_job.html", {
        "job": job
    })

def job_details(request, id):
    job = get_object_or_404(JobPost.objects.select_related("employer"), id=id)
    user = request.user
    is_owner = user.is_authenticated and job.employer.employer_id == user.pk
    is_admin = user.is_authenticated and (user.role == "admin" or user.is_superuser)
    if not job.is_public and not (is_owner or is_admin):
        from django.http import Http404
        raise Http404()

    return render(request, "pages/job_details.html", {
        "job": job
    })

def company_profile(request, id):
    company = get_object_or_404(Employer, id=id)
    user = request.user
    is_owner = user.is_authenticated and company.employer_id == user.pk
    is_admin = user.is_authenticated and (user.role == "admin" or user.is_superuser)
    if not (company.approval_status == "approved" and company.is_active) and not (is_owner or is_admin):
        from django.http import Http404
        raise Http404()

    jobs = JobPost.objects.public().filter(employer=company)

    return render(request, "pages/company_profile.html", {
        "company": company,
        "jobs": jobs,
    })


@login_required(login_url='login-user')
def employer_company_profile(request):
    if request.user.role != 'employer':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Employer access required.')
    employer = get_object_or_404(Employer, employer=request.user)
    applications = JobApplication.objects.filter(job__employer=employer)
    today = timezone.localdate()
    stats = {
        'active_jobs': employer.jobs.filter(status='approved', deadline__gte=today).count(),
        'applicants': applications.count(),
        'hired': applications.filter(status='hired').count(),
        'awaiting': applications.filter(status__in=['pending', 'reviewing']).count(),
    }
    about = (employer.description or '').strip()
    checklist = [
        ('Company logo', bool(employer.company_logo)),
        ('About the company (100+ characters)', len(about) >= 100),
        ('Mobile number', bool(employer.contact_no)),
        ('Company email', bool(employer.employer.email)),
    ]
    completeness = round(sum(done for _, done in checklist) / len(checklist) * 100)
    recent_jobs = (employer.jobs.annotate(application_count=Count('applications'))
                   .order_by('-created_at')[:5])
    return render(request, 'pages/employer_company_profile.html', {
        'employer': employer, 'stats': stats, 'checklist': checklist,
        'completeness': completeness, 'about_too_short': len(about) < 100, 'recent_jobs': recent_jobs,
    })


@login_required(login_url='login-user')
def edit_employer_company_profile(request):
    if request.user.role != 'employer':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Employer access required.')
    employer = get_object_or_404(Employer, employer=request.user)
    form = CompanyProfileForm(request.POST or None, request.FILES or None, instance=employer)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            request.user.email = form.cleaned_data['email']
            request.user.save(update_fields=['email'])
        return redirect('employer-company-profile')
    return render(request, 'pages/edit_employer_company_profile.html', {'employer': employer, 'form': form})


@login_required(login_url="login-user")
def apply_job(request, id):

    # =========================================================
    # GET JOB
    # =========================================================

    job = get_object_or_404(
        JobPost,
        id=id
    )

    # =========================================================
    # GET APPLICANT PROFILE
    # =========================================================

    try:

        applicant = request.user.applicant_profile

    except AttributeError:

        messages.error(
            request,
            "Applicant profile not found."
        )

        return redirect(
            "job_details",
            id=job.id
        )

    # =========================================================
    # ONLY APPROVED JOBS CAN RECEIVE APPLICATIONS
    # =========================================================

    if not job.is_public or job.deadline < timezone.localdate():

        messages.error(
            request,
            "This job is not currently accepting applications."
        )

        return redirect(
            "job_details",
            id=job.id
        )

    # =========================================================
    # CHECK DUPLICATE APPLICATION
    # =========================================================

    existing_application = JobApplication.objects.filter(
        job=job,
        applicant=applicant
    ).first()

    if existing_application:

        messages.warning(
            request,
            "You have already applied for this job."
        )

        return redirect(
            "my-applications"
        )

    # =========================================================
    # PROCESS APPLICATION
    # =========================================================

    if request.method == "POST":

        message = request.POST.get(
            "message",
            ""
        ).strip()

        uploaded_resume = request.FILES.get(
            "resume"
        )

        uploaded_cover_letter = request.FILES.get(
            "cover_letter"
        )

        # =====================================================
        # FILE VALIDATION FUNCTION
        # =====================================================

        def validate_file(uploaded_file, field_name):

            if not uploaded_file:
                return None

            # Maximum 5 MB
            max_size = 5 * 1024 * 1024

            if uploaded_file.size > max_size:

                return (
                    f"{field_name} must not exceed 5 MB."
                )

            allowed_extensions = [
                ".pdf",
                ".doc",
                ".docx"
            ]

            extension = os.path.splitext(
                uploaded_file.name
            )[1].lower()

            if extension not in allowed_extensions:

                return (
                    f"{field_name} must be a PDF, DOC, or DOCX file."
                )

            return None

        # =====================================================
        # VALIDATE RESUME
        # =====================================================

        resume_error = validate_file(
            uploaded_resume,
            "Resume"
        )
        resume_error = resume_error or inspect_resume(uploaded_resume)["error"]

        if resume_error:

            messages.error(
                request,
                resume_error
            )

            return render(
                request,
                "pages/apply_job.html",
                {
                    "job": job,
                    "applicant": applicant,
                    "existing_application": existing_application,
                    "resume_error": resume_error,
                }
            )

        # =====================================================
        # VALIDATE COVER LETTER
        # =====================================================

        cover_letter_error = validate_file(
            uploaded_cover_letter,
            "Cover letter"
        )

        if cover_letter_error:

            messages.error(
                request,
                cover_letter_error
            )

            return render(
                request,
                "pages/apply_job.html",
                {
                    "job": job,
                    "applicant": applicant,
                    "existing_application": existing_application,
                }
            )

        # =====================================================
        # REQUIRE RESUME
        #
        # Either:
        # - newly uploaded resume
        # - existing applicant resume
        # =====================================================

        if not uploaded_resume and not applicant.resume:

            messages.error(
                request,
                "Please upload a resume before submitting your application."
            )

            return render(
                request,
                "pages/apply_job.html",
                {
                    "job": job,
                    "applicant": applicant,
                    "existing_application": existing_application,
                }
            )

        # =====================================================
        # REQUIRE COVER LETTER
        #
        # Either:
        # - newly uploaded cover letter
        # - existing applicant cover letter
        # =====================================================

        if (
            not uploaded_cover_letter
            and not applicant.cover_letter
        ):

            messages.error(
                request,
                "Please upload a cover letter before submitting your application."
            )

            return render(
                request,
                "pages/apply_job.html",
                {
                    "job": job,
                    "applicant": applicant,
                    "existing_application": existing_application,
                }
            )

        # =====================================================
        # CREATE APPLICATION
        # =====================================================

        application = JobApplication.objects.create(
            job=job,
            applicant=applicant,
            message=message,
            status="pending"
        )

        # =====================================================
        # SAVE RESUME
        #
        # If a new resume was uploaded:
        #     save the uploaded file
        #
        # Otherwise:
        #     copy the applicant's existing file
        # =====================================================

        if uploaded_resume:

            application.resume = uploaded_resume

        elif applicant.resume:

            source_path = applicant.resume.path

            if os.path.exists(source_path):

                with open(
                    source_path,
                    "rb"
                ) as resume_file:

                    application.resume.save(
                        os.path.basename(
                            source_path
                        ),
                        File(resume_file),
                        save=False
                    )

        # =====================================================
        # SAVE COVER LETTER
        #
        # If a new cover letter was uploaded:
        #     save the uploaded file
        #
        # Otherwise:
        #     copy the applicant's existing file
        # =====================================================

        if uploaded_cover_letter:

            application.cover_letter = uploaded_cover_letter

        elif applicant.cover_letter:

            source_path = applicant.cover_letter.path

            if os.path.exists(source_path):

                with open(
                    source_path,
                    "rb"
                ) as cover_letter_file:

                    application.cover_letter.save(
                        os.path.basename(
                            source_path
                        ),
                        File(cover_letter_file),
                        save=False
                    )

        # =====================================================
        # FINAL SAVE
        # =====================================================

        application.save()

        # =====================================================
        # SUCCESS MESSAGE
        # =====================================================

        messages.success(
            request,
            f"Your application for {job.title} has been submitted successfully."
        )

        return redirect(
            "my-applications"
        )

    # =========================================================
    # DISPLAY APPLICATION PAGE
    # =========================================================

    return render(
        request,
        "pages/apply_job.html",
        {
            "job": job,
            "applicant": applicant,
            "existing_application": existing_application,
        }
    )

@login_required(login_url="login-user")
def my_applications(request):
    applicant = getattr(request.user, "applicant_profile", None)

    if applicant is None:
        applications = JobApplication.objects.none()
    else:
        applications = JobApplication.objects.filter(
            applicant=applicant
        ).order_by("-applied_at")

    return render(
        request,
        "pages/my_applications.html",
        {
            "applications": applications,
            "has_applicant_profile": applicant is not None,
        }
    )

@login_required(login_url="login-user")
def applicants(request):
    from django.core.paginator import Paginator
    from .skill_extraction import experience_matches, skill_in_text
    employer = get_object_or_404(Employer, employer=request.user)
    jobs = employer.jobs.order_by('title')
    status = request.GET.get('status', '')
    skill = request.GET.get('skill', '').strip()[:60]
    experience = request.GET.get('experience', '')
    job_id = request.GET.get('job', '')
    applications = JobApplication.objects.filter(job__employer=employer).select_related(
        'applicant', 'applicant__user', 'job', 'assessment',
    ).prefetch_related('applicant__certificates', 'applicant__work_experiences').order_by('-applied_at', '-pk')
    if status:
        applications = applications.filter(status=status)
    if job_id:
        applications = applications.filter(job_id=int(job_id)) if job_id.isdecimal() else applications.none()
    from employer.job_demand import success_history, likelihood
    history = success_history()
    from employer.benchmarks import build_benchmarks, compare
    benchmarks = build_benchmarks()
    results = []
    for application in applications:
        person = application.applicant
        confirmed = [s.strip() for s in re.split(r'[,;\n|]+', person.skills or '') if s.strip()]
        experiences = list(person.work_experiences.all())
        matched_experience = experience_matches(application.job, experiences)
        job_text = ' '.join([application.job.title, application.job.description, application.job.qualifications, application.job.responsibilities])
        application.matched_skills = [s for s in confirmed if skill_in_text(s, job_text)]
        application.matched_experience = matched_experience
        application.confirmed_skills = confirmed
        application.match = candidate_match(application.job, confirmed, experiences)
        application.success_likelihood = likelihood(application, history, application.match['score'])
        application.benchmark = compare(application, benchmarks, application.match['score'], confirmed, experiences)
        if skill and not any(skill_in_text(skill, s) or skill_in_text(s, skill) for s in confirmed):
            continue
        if experience == 'relevant' and not matched_experience:
            continue
        if experience == 'any' and not experiences:
            continue
        if experience == 'none' and experiences:
            continue
        results.append(application)
    sort = request.GET.get('sort', 'match')
    if sort == 'likelihood':
        results.sort(key=lambda item: (item.success_likelihood is not None,
                                       item.success_likelihood['percent'] if item.success_likelihood else -1,
                                       item.match['score'] if item.match['score'] is not None else -1, item.pk), reverse=True)
    elif sort != 'recent':
        sort = 'match'
    if sort == 'match':
        results.sort(key=lambda item: (item.match['score'] is not None, item.match['score'] if item.match['score'] is not None else -1, item.applied_at, item.pk), reverse=True)
    page = Paginator(results, 10).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'pages/applicants.html', {
        'applications':page, 'page_obj':page, 'result_count':len(results), 'filter_jobs':jobs,
        'status_choices':JobApplication.STATUS_CHOICES, 'filter_status':status,
        'filter_skill':skill, 'filter_experience':experience, 'filter_job':job_id,
        'page_query':params.urlencode(), 'filter_sort':sort,
    })


@login_required(login_url="login-user")
def update_applicant_status(request, id):

    application = get_object_or_404(
        JobApplication,
        id=id
    )

    # ==========================================
    # ONLY THE EMPLOYER WHO OWNS THE JOB
    # CAN UPDATE THE APPLICATION
    # ==========================================

    if application.job.employer != request.user.employer:

        return redirect(
            "applicants"
        )

    # ==========================================
    # ONLY PROCESS POST REQUEST
    # ==========================================

    if request.method == "POST":

        new_status = request.POST.get(
            "status"
        )

        # ==========================================
        # VALID STATUS VALUES
        # ==========================================

        if new_status in [
            "pending",
            "reviewing",
            "shortlisted",
            "offered",
            "rejected",
        ]:

            # ==========================================
            # ONLY PROCEED IF STATUS CHANGED
            # ==========================================

            if application.status != new_status:

                # ======================================
                # UPDATE APPLICATION STATUS
                # ======================================

                try:
                    changed = change_application_status(application.pk, request.user.employer.pk, new_status)
                except ValueError as error:
                    messages.error(request, str(error))
                    return redirect('applicants')
                if not changed:
                    return redirect('applicants')
                application.status = new_status

                # ======================================
                # GET APPLICANT PHONE NUMBER
                # ======================================

                phone = application.applicant.phone_number

                # ======================================
                # FORMAT PHILIPPINE MOBILE NUMBER
                # 0917xxxxxxx
                #       ↓
                # 63917xxxxxxx
                # ======================================

                phone = format_ph_mobile(
                    phone
                )

                # ======================================
                # PENDING
                # ======================================

                if application.status == "pending":

                    message = (
                        f"Dear {application.applicant.first_name},\n\n"
                        f"Your application for the position of "
                        f"{application.job.title} at "
                        f"{application.job.employer.company_name} "
                        f"has been successfully received.\n\n"
                        f"Our recruitment team will review your "
                        f"application, and you will be notified once "
                        f"there are updates.\n\n"
                        f"Thank you for your interest in joining "
                        f"our organization.\n\n"
                        f"{application.job.employer.company_name}"
                    )

                # ======================================
                # REVIEWING
                # ======================================

                elif application.status == "reviewing":

                    message = (
                        f"Dear {application.applicant.first_name},\n\n"
                        f"We would like to inform you that your "
                        f"application for the position of "
                        f"{application.job.title} at "
                        f"{application.job.employer.company_name} "
                        f"is currently under review.\n\n"
                        f"We appreciate your patience and will keep "
                        f"you informed of any further developments.\n\n"
                        f"Thank you.\n"
                        f"{application.job.employer.company_name}"
                    )

                # ======================================
                # SHORTLISTED
                # ======================================

                elif application.status == "shortlisted":

                    message = (
                        f"Dear {application.applicant.first_name},\n\n"
                        f"Congratulations! You have been shortlisted "
                        f"for the position of "
                        f"{application.job.title} at "
                        f"{application.job.employer.company_name}.\n\n"
                        f"Our Human Resources team will contact you "
                        f"soon regarding the next stage of the "
                        f"recruitment process.\n\n"
                        f"Thank you, and we look forward to "
                        f"speaking with you.\n\n"
                        f"{application.job.employer.company_name}"
                    )

                # ======================================
                # ACCEPTED
                # ======================================

                elif application.status == "offered":
                    message = f"You have a job offer for {application.job.title} at {application.job.employer.company_name}. Log in and open My Applications to accept or decline."

                elif application.status == "accepted":

                    message = (
                        f"Dear {application.applicant.first_name},\n\n"
                        f"Congratulations! We are pleased to inform "
                        f"you that you have been selected for the "
                        f"position of {application.job.title} at "
                        f"{application.job.employer.company_name}.\n\n"
                        f"Our Human Resources team will contact you "
                        f"shortly with further instructions regarding "
                        f"your employment.\n\n"
                        f"Welcome to the team, and we wish you "
                        f"every success.\n\n"
                        f"Sincerely,\n"
                        f"{application.job.employer.company_name}"
                    )

                # ======================================
                # REJECTED
                # ======================================

                elif application.status == "rejected":

                    message = (
                        f"Dear {application.applicant.first_name},\n\n"
                        f"Thank you for your interest in the "
                        f"{application.job.title} position at "
                        f"{application.job.employer.company_name}.\n\n"
                        f"After careful evaluation, we regret to "
                        f"inform you that you have not been selected "
                        f"for this opportunity.\n\n"
                        f"We sincerely appreciate the time and effort "
                        f"you invested in your application and "
                        f"encourage you to apply for future "
                        f"opportunities with us.\n\n"
                        f"We wish you success in your future career.\n\n"
                        f"Sincerely,\n"
                        f"{application.job.employer.company_name}"
                    )

                # ======================================
                # NOTIFY APPLICANT BY SMS
                # (failures are logged; the status change still stands)
                # ======================================

                message = f"{SMS_BRAND}\n\n{message}"
                if not send_sms(phone, message).ok:
                    messages.warning(request, "Status updated, but the SMS notification could not be sent.")

    # ==========================================
    # RETURN TO APPLICANTS
    # ==========================================

    return redirect(
        "applicants"
    )


@login_required(login_url="login-user")
def applicant_profile(request):
    applicant = getattr(request.user, "applicant_profile", None)
    skill_tags = [s.strip() for s in re.split(r'[,;\n|]+', applicant.skills or '') if s.strip()] if applicant else []
    context = {"applicant": applicant, "skill_tags": skill_tags}
    if applicant:
        experiences = list(applicant.work_experiences.all())
        certificate_count = applicant.certificates.count()
        applications = JobApplication.objects.filter(applicant=applicant)
        by_status = dict(applications.values_list("status").annotate(n=Count("pk")))
        profile_items = [
            ('Profile photo', bool(applicant.profile_photo)),
            ('Email and mobile number', bool(applicant.email and applicant.phone_number)),
            ('At least 3 skills', len(skill_tags) >= 3),
            ('Resume uploaded', bool(applicant.resume)),
            ('Cover letter uploaded', bool(applicant.cover_letter)),
            ('Work experience or certificate', bool(experiences or certificate_count)),
        ]
        context.update(
            experiences=experiences,
            certificate_count=certificate_count,
            profile_items=profile_items,
            profile_completion=round(sum(done for _, done in profile_items) / len(profile_items) * 100),
            stats={
                "applied": sum(by_status.values()),
                "in_review": sum(by_status.get(k, 0) for k in ("pending", "reviewing", "shortlisted", "accepted")),
                "offers": by_status.get("offered", 0),
                "hired": by_status.get("hired", 0),
            },
            recent_applications=applications.select_related("job", "job__employer").order_by("-applied_at")[:5],
        )
    return render(request, "pages/applicant_profile.html", context)

@login_required(login_url="login-user")
def edit_applicant_profile(request):
    applicant = get_object_or_404(
        Applicant,
        user=request.user,
    )

    errors = {}

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        middle_name = request.POST.get("middle_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        skills = request.POST.get("skills", "").strip()

        resume = request.FILES.get("resume")
        cover_letter = request.FILES.get("cover_letter")

        # Required fields
        if not first_name:
            errors["first_name"] = "First name is required."

        if not last_name:
            errors["last_name"] = "Last name is required."

        if not email:
            errors["email"] = "Email address is required."
        else:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError

            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

            if Applicant.objects.filter(
                email__iexact=email
            ).exclude(pk=applicant.pk).exists():
                errors["email"] = "This email is already used by another applicant."

            if request.user.__class__.objects.filter(
                email__iexact=email
            ).exclude(pk=request.user.pk).exists():
                errors["email"] = "This email is already associated with another account."

        if not phone_number:
            errors["phone_number"] = "Mobile number is required."
        elif not phone_number.isdigit() or len(phone_number) != 11 or not phone_number.startswith("09"):
            errors["phone_number"] = "Enter a valid 11-digit Philippine mobile number starting with 09."
        elif Applicant.objects.filter(phone_number=phone_number).exclude(pk=applicant.pk).exists():
            errors["phone_number"] = "This mobile number is already used by another account."

        errors.update(applicant_field_errors(request.POST))
        resume_result = inspect_resume(resume)
        if resume_result["error"]:
            errors["resume"] = resume_result["error"]

        # Optional file validation
        allowed_extensions = {".pdf", ".doc", ".docx"}

        from pathlib import Path

        for field_name, uploaded_file in (
            ("resume", resume),
            ("cover_letter", cover_letter),
        ):
            if uploaded_file:
                extension = Path(uploaded_file.name).suffix.lower()

                if extension not in allowed_extensions:
                    errors[field_name] = "Only PDF, DOC, and DOCX files are allowed."
                elif uploaded_file.size > 5 * 1024 * 1024:
                    errors[field_name] = "The file must not exceed 5 MB."

        if not errors:
            with transaction.atomic():
                applicant.first_name = first_name
                applicant.middle_name = middle_name
                applicant.last_name = last_name
                applicant.email = email
                applicant.phone_number = phone_number
                applicant.skills = skills

                if resume:
                    applicant.resume = resume

                if cover_letter:
                    applicant.cover_letter = cover_letter

                applicant.save()

                request.user.email = email
                request.user.save(update_fields=["email"])

            return redirect("applicant-profile")

    return render(
        request,
        "pages/edit_applicant_profile.html",
        {
            "applicant": applicant,
            "errors": errors,
            "form_data": request.POST if request.method == "POST" else {},
        },
    )
