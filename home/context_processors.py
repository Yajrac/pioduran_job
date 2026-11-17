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


EXTRA_SKILLS = [
    "Food Preparation", "Baking", "Housekeeping", "Caregiving", "First Aid", "Security",
    "Masonry", "Motorcycle Driving", "Basic Math", "MS Office", "Troubleshooting",
    "Computer Repair", "Fish Handling", "Farming", "Customer Handling", "Physical Fitness",
]


def job_categories(request):
    """Category options and skill suggestions for the job post form."""
    from .skill_extraction import SKILLS
    suggestions = sorted(set(SKILLS) | set(EXTRA_SKILLS), key=str.casefold)
    return {"category_choices": CATEGORY_CHOICES, "skill_suggestions": suggestions}
