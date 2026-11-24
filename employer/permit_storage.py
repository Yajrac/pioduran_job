from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def permit_storage():
    """Business permits are private: kept outside MEDIA_ROOT and served only through an access-checked view."""
    return FileSystemStorage(location=settings.BASE_DIR / "private_uploads", base_url=None)


def permit_path(instance, filename):
    return f"business_permits/{uuid4().hex}{Path(filename).suffix.lower()}"
