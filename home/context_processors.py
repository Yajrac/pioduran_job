from employer.job_categories import CATEGORY_CHOICES


def demo_sms(request):
    """The on-screen 'SMS' for verify pages - only in local demo mode."""
    from django.conf import settings
    if not (settings.DEBUG and getattr(settings, "OTP_DEV_MODE", False)):
        return {}
    path = request.path.rstrip("/")
    if not (path.endswith("/registration/verify") or path.endswith("/forgot-password/verify")):
        return {}
    return {"demo_sms": request.session.get("demo_sms")}


def job_categories(request):
    """Category options for the job post form."""
    return {"category_choices": CATEGORY_CHOICES}
