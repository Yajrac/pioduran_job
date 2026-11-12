from django.shortcuts import render
from django.urls import reverse


def server_error(request):
    return render(request, "errors/500.html", status=500)


def page_not_found(request, exception=None):
    user = getattr(request, "user", None)
    role = getattr(user, "role", "") if user and user.is_authenticated else ""
    destinations = {
        "admin": ("peso-dashboard", "Back to Admin Dashboard", "PESO Admin"),
        "employer": ("employer-dashboard", "Back to Employer Dashboard", "Employer Portal"),
        "applicant": ("browse-job", "Browse Jobs", "Applicant Portal"),
    }
    route, label, portal = destinations.get(role, ("home", "Back to Home", "PESO Pio Duran"))
    return render(request, "errors/404.html", {
        "return_url": reverse(route), "return_label": label, "portal_name": portal,
    }, status=404)
