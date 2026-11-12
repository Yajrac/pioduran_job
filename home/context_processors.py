from employer.job_categories import CATEGORY_CHOICES


def demo_sms(request):
    """The on-screen 'SMS' for verify pages - only in local demo mode."""
    from django.conf import settings
    if not (settings.DEBUG and getattr(settings, "OTP_DEV_MODE", False)):
        return {}
    if not request.path.rstrip("/").endswith("/registration/verify"):
        return {}
    return {"demo_sms": request.session.get("demo_sms")}


def job_categories(request):
    """Category options for the job post form."""
    return {"category_choices": CATEGORY_CHOICES}
