"""Navigation state for the PESO admin layout (core/templates/base.html).

Server-side so the current section is always highlighted (including detail
pages) and the sidebar can show how many items are waiting for review.
"""
from django.urls import reverse

# url_name -> (sidebar section, page title, parent url_name or None)
PAGES = {
    "peso-dashboard": ("dashboard", "Dashboard", None),
    "employer-list": ("employers", "Employers", None),
    "employer_detail": ("employers", "Employer Profile", "employer-list"),
    "applicant-list": ("applicants", "Applicants", None),
    "job-post-list": ("jobs", "Job Posts", None),
    "view-job": ("jobs", "Job Post Details", "job-post-list"),
    "approved-job": ("jobs", "Review Job Post", "job-post-list"),
    "reports": ("reports", "Reports", None),
    "admin-settings": ("settings", "Settings", None),
}
REPORT_TITLES = {
    "employers": "Employer Records", "applicants": "Applicant Records", "jobs": "Job Records",
    "hired": "Hired Records", "demand": "Job Demand Ranking", "assessments": "Assessment & Benchmarks",
}


def admin_nav(request):
    match = getattr(request, "resolver_match", None)
    user = getattr(request, "user", None)
    if not match or not request.path.startswith("/peso/") or not (user and user.is_authenticated):
        return {}
    section, title, parent = PAGES.get(match.url_name, (None, None, None))
    if section is None:
        return {}
    crumbs = [("PESO Admin", reverse("peso-dashboard"))]
    if parent:
        parent_title = PAGES[parent][1]
        crumbs.append((parent_title, reverse(parent)))
    if match.url_name == "reports":
        crumbs.append(("Reports", None))
        title = REPORT_TITLES.get(request.GET.get("section", "employers"), "Reports")
    if match.url_name != "peso-dashboard":
        crumbs.append((title, None))

    from employer.models import Employer, JobPost
    return {
        "admin_nav_section": section,
        "admin_page_title": title,
        "admin_breadcrumbs": crumbs,
        "admin_pending_employers": Employer.objects.filter(approval_status="pending").count(),
        "admin_pending_jobs": JobPost.objects.filter(status="pending").count(),
    }
