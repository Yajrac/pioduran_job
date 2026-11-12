from uuid import uuid4
from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def certificate_storage():
    return FileSystemStorage(location=settings.BASE_DIR / "private_uploads", base_url=None)


def certificate_path(instance, filename):
    return f"certificates/{instance.applicant_id}/{uuid4().hex}{Path(filename).suffix.lower()}"
