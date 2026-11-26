"""Access-controlled, view-only resumes and cover letters (see document_viewer.py).

These files contain personal data, so they are never linked through the
public /media/ URL. Each request checks who is asking for the file.
"""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse

from applicant.models import Applicant
from employer.models import JobApplication

from .document_viewer import render_document

KINDS = {"resume", "cover_letter"}
LABELS = {"resume": "Resume", "cover_letter": "Cover letter"}


def _name(applicant):
    return " ".join(filter(None, [applicant.first_name, applicant.last_name])) or applicant.user.username


@login_required(login_url="login-user")
def my_document(request, kind):
    """The logged-in applicant's own profile resume or cover letter."""
    if kind not in KINDS:
        raise Http404()
    applicant = get_object_or_404(Applicant, user=request.user)
    return render_document(request, getattr(applicant, kind), LABELS[kind], _name(applicant),
                           reupload_url=reverse("edit-applicant-profile") + "#" + kind)


@login_required(login_url="login-user")
def application_document(request, pk, kind):
    """A document submitted with an application.

    Allowed: the applicant, the employer that owns the job, and PESO admins.
    """
    if kind not in KINDS:
        raise Http404()
    application = get_object_or_404(
        JobApplication.objects.select_related("applicant", "job__employer"), pk=pk,
    )
    user = request.user
    allowed = (
        application.applicant.user_id == user.pk
        or application.job.employer.employer_id == user.pk
        or user.role == "admin"
        or user.is_superuser
    )
    if not allowed:
        raise Http404()
    field = getattr(application, kind) or getattr(application.applicant, kind)
    own = application.applicant.user_id == user.pk
    return render_document(request, field, f"{LABELS[kind]} \u00b7 {_name(application.applicant)}",
                           f"Applied for {application.job.title}",
                           reupload_url=reverse("edit-applicant-profile") + "#" + kind if own else None)
