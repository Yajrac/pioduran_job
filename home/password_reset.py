"""Forgot password for applicants and employers, by SMS code.

Flow: mobile number -> 6-digit SMS code ->
[choose the account, when one number has several] -> new password.

Security notes
* The same message is shown whether or not an account matched, so the page
  cannot be used to find out who has an account.
* Codes are hashed, expire in 5 minutes, allow 5 wrong tries and work once.
* At most 3 codes per number per hour, and 60 seconds between resends.
* PESO admin and superuser accounts can never be reset here.
* Changing the password signs out every other session of that account.
"""
import re
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer

from .landing import signed_in_users_go_home
from .models import PasswordResetCode
from .sms import SMS_BRAND, send_sms

CODE_MINUTES = 5
MAX_ATTEMPTS = 5
MAX_CODES_PER_HOUR = 3
RESEND_SECONDS = 60
VERIFIED_MINUTES = 10
SESSION_KEY = "pwreset"
TEMPLATE = "pages/forgot_password.html"
GENERIC_SENT = ("If an account matches what you entered, we sent a 6-digit code "
                "to its registered mobile number.")


# --------------------------------------------------------------- helpers

def normalize_phone(value):
    """09171234567 / +639171234567 / 0917 123 4567 -> 09171234567, else ''."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("63") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits if re.fullmatch(r"09\d{9}", digits) else ""


def mask_phone(phone):
    return phone[:4] + "•••" + phone[-4:] if len(phone) == 11 else ""


def eligible(user):
    return bool(user and user.is_active and not user.is_superuser and user.role in ("applicant", "employer"))


def accounts_on_phone(phone):
    users = [a.user for a in Applicant.objects.filter(phone_number=phone).select_related("user")]
    users += [e.employer for e in Employer.objects.filter(contact_no=phone).select_related("employer")]
    unique = {u.pk: u for u in users if eligible(u)}
    return sorted(unique.values(), key=lambda u: (u.role, u.username.lower()))


def resolve(identifier):
    """(phone, None) when an applicant/employer account uses this mobile number,
    else (None, None). Only a mobile number is accepted (no username or email)."""
    phone = normalize_phone(identifier)
    if phone and accounts_on_phone(phone):
        return phone, None
    return None, None


def account_label(user):
    if user.role == "employer":
        employer = Employer.objects.filter(employer=user).first()
        return f"Employer · {employer.company_name}" if employer else "Employer"
    profile = Applicant.objects.filter(user=user).first()
    name = f"{profile.first_name} {profile.last_name}".strip() if profile else ""
    return f"Applicant · {name}" if name else "Applicant"


def _state(request):
    return request.session.get(SESSION_KEY) or {}


def _save_state(request, **values):
    state = _state(request)
    state.update(values)
    request.session[SESSION_KEY] = state


def _current_code(request):
    code_id = _state(request).get("code_id")
    return PasswordResetCode.objects.filter(pk=code_id).select_related("user").first() if code_id else None


def _send_code(request, phone, user):
    """Create and text a new code unless the hourly limit is reached."""
    from .views import generate_otp, remember_demo_sms
    now = timezone.now()
    if PasswordResetCode.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1)).count() >= MAX_CODES_PER_HOUR:
        return None
    PasswordResetCode.objects.filter(phone=phone, used_at__isnull=True).update(used_at=now)  # older codes stop working
    code = generate_otp()
    record = PasswordResetCode.objects.create(phone=phone, user=user, code_hash=make_password(code),
                                              expires_at=now + timedelta(minutes=CODE_MINUTES))
    message = (f"{SMS_BRAND}: Your password reset code is {code}. It expires in {CODE_MINUTES} minutes. "
               "If you did not request this, ignore this message.")
    send_sms(phone, message)  # failures are logged; the page message stays the same either way
    remember_demo_sms(request, phone, message, code)
    return record


def _verified(request):
    state = _state(request)
    record = _current_code(request)
    if not (state.get("verified") and record and not record.used_at):
        return None
    verified_at = datetime.fromisoformat(state.get("verified_at"))
    if timezone.now() - verified_at > timedelta(minutes=VERIFIED_MINUTES):
        return None
    return record


def _allowed_accounts(record):
    if record.user_id:
        return [record.user] if eligible(record.user) else []
    return accounts_on_phone(record.phone)


# ----------------------------------------------------------------- views

@signed_in_users_go_home()
def forgot_password(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        if not normalize_phone(identifier):
            return render(request, TEMPLATE, {"step": "identify", "identifier": identifier,
                                              "error": "Enter an 11-digit mobile number starting with 09."})
        request.session.pop(SESSION_KEY, None)
        request.session.pop("demo_sms", None)
        phone, user = resolve(identifier)
        record = _send_code(request, phone, user) if phone else None
        _save_state(request, code_id=record.pk if record else None, wrong=0, verified=False,
                    sent_at=timezone.now().isoformat())
        messages.info(request, GENERIC_SENT, extra_tags="password_reset")
        return redirect("forgot-password-verify")
    return render(request, TEMPLATE, {"step": "identify"})


@signed_in_users_go_home()
def verify_code(request):
    state = _state(request)
    if "sent_at" not in state:
        return redirect("forgot-password")
    context = {"step": "verify"}
    if request.method == "POST":
        code = re.sub(r"\D", "", request.POST.get("otp", ""))
        record = _current_code(request)
        now = timezone.now()
        if not record:
            wrong = state.get("wrong", 0) + 1
            _save_state(request, wrong=wrong)
            context["error"] = ("Too many wrong attempts. Please start again." if wrong >= MAX_ATTEMPTS
                                else "The code is incorrect or has expired.")
        elif record.used_at or record.expires_at < now:
            context["error"] = "This code has expired. Request a new code."
        elif record.attempts >= MAX_ATTEMPTS:
            context["error"] = "Too many wrong attempts. Request a new code."
        elif not check_password(code, record.code_hash):
            record.attempts += 1
            record.save(update_fields=["attempts"])
            left = MAX_ATTEMPTS - record.attempts
            context["error"] = (f"Incorrect code. {left} attempt{'s' if left != 1 else ''} left." if left
                                else "Too many wrong attempts. Request a new code.")
        else:
            accounts = _allowed_accounts(record)
            if not accounts:
                context["error"] = "This code has expired. Request a new code."
            else:
                request.session.pop("demo_sms", None)
                _save_state(request, verified=True, verified_at=now.isoformat(),
                            user_id=accounts[0].pk if len(accounts) == 1 else None)
                return redirect("forgot-password-new" if len(accounts) == 1 else "forgot-password-account")
    return render(request, TEMPLATE, context)


@signed_in_users_go_home()
def resend_code(request):
    state = _state(request)
    if request.method != "POST" or "sent_at" not in state:
        return redirect("forgot-password")
    sent_at = datetime.fromisoformat(state["sent_at"])
    if timezone.now() - sent_at < timedelta(seconds=RESEND_SECONDS):
        messages.warning(request, f"Please wait {RESEND_SECONDS} seconds before requesting another code.",
                         extra_tags="password_reset")
        return redirect("forgot-password-verify")
    record = _current_code(request)
    if record:
        new = _send_code(request, record.phone, record.user)
        if new:
            _save_state(request, code_id=new.pk)
    _save_state(request, sent_at=timezone.now().isoformat(), wrong=0)
    messages.info(request, GENERIC_SENT, extra_tags="password_reset")
    return redirect("forgot-password-verify")


@signed_in_users_go_home()
def choose_account(request):
    record = _verified(request)
    if not record:
        return redirect("forgot-password")
    accounts = _allowed_accounts(record)
    if request.method == "POST":
        chosen = next((u for u in accounts if str(u.pk) == request.POST.get("account")), None)
        if chosen:
            _save_state(request, user_id=chosen.pk)
            return redirect("forgot-password-new")
    options = [{"id": u.pk, "username": u.username, "label": account_label(u)} for u in accounts]
    return render(request, TEMPLATE, {"step": "choose", "accounts": options, "phone": mask_phone(record.phone)})


@signed_in_users_go_home()
def new_password(request):
    record = _verified(request)
    user_id = _state(request).get("user_id")
    user = next((u for u in _allowed_accounts(record) if u.pk == user_id), None) if record else None
    if not user:
        return redirect("forgot-password")
    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()  # new hash -> every existing session of this account is signed out
        now = timezone.now()
        PasswordResetCode.objects.filter(phone=record.phone, used_at__isnull=True).update(used_at=now)
        request.session.pop(SESSION_KEY, None)
        send_sms(record.phone, f"{SMS_BRAND}: Your password was changed. If this wasn't you, "
                               "contact PESO Pio Duran right away.")
        messages.success(request, "Your password was changed. Sign in with your new password.",
                         extra_tags="password_reset")
        return redirect("login-user")
    return render(request, TEMPLATE, {"step": "new", "form": form, "username": user.username})
