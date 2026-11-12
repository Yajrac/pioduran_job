"""Access-controlled downloads for resumes and cover letters.

These files contain personal data, so they are never linked through the
public /media/ URL. Each request checks who is asking for the file.
"""
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from applicant.models import Applicant
from employer.models import JobApplication

KINDS = {"resume", "cover_letter"}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _file_response(field, label):
    if not field:
        raise Http404()
    try:
        handle = field.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404()
    extension = Path(field.name).suffix.lower()
    content_type = CONTENT_TYPES.get(extension, "application/octet-stream")
    # PDFs open in the browser; Word files download.
    response = FileResponse(handle, content_type=content_type,
                            as_attachment=extension != ".pdf", filename=label + extension)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required(login_url="login-user")
def my_document(request, kind):
    """The logged-in applicant's own profile resume or cover letter."""
    if kind not in KINDS:
        raise Http404()
    applicant = get_object_or_404(Applicant, user=request.user)
    return _file_response(getattr(applicant, kind), kind.replace("_", "-"))


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
    return _file_response(field, kind.replace("_", "-"))
