from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from employer.models import Employer

CONTENT_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@login_required(login_url="login-user")
def business_permit(request, pk):
    """An employer's uploaded business permit. Only PESO admins and the employer themselves may open it."""
    employer = get_object_or_404(Employer, pk=pk)
    user = request.user
    if not (user.role == "admin" or user.is_superuser or employer.employer_id == user.pk):
        raise Http404()
    if not employer.business_permit_file:
        raise Http404()
    extension = Path(employer.business_permit_file.name).suffix.lower()
    if extension not in CONTENT_TYPES:
        raise Http404()
    try:
        file = employer.business_permit_file.open("rb")
    except FileNotFoundError:
        raise Http404()
    response = FileResponse(file, content_type=CONTENT_TYPES[extension], filename="business-permit" + extension)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
