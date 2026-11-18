"""Signed-in users skip the public landing pages and go to their own page.

    PESO admin -> Admin Dashboard
    Employer   -> Employer Overview (pending/rejected employers are sent on
                  to the Approval Status page by the approval middleware)
    Applicant  -> My Profile

Used on Home, Log In (public and admin), registration and Forgot Password.
Browse Jobs, Job Details and Company Profile stay open to everyone.
"""
from functools import wraps

from django.shortcuts import redirect


def home_url_name(user):
    if user.is_superuser or getattr(user, "role", "") == "admin":
        return "peso-dashboard"
    if user.role == "employer":
        return "employer-dashboard"
    if user.role == "applicant":
        return "applicant-profile"
    return None


def signed_in_users_go_home(methods=("GET", "HEAD", "POST")):
    """Decorator: redirect an authenticated user to their own page for the given methods."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.is_authenticated and request.method in methods:
                target = home_url_name(request.user)
                if target:
                    return redirect(target)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
