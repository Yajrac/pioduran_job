"""View-only document viewer for resumes, cover letters and certificates.

The file itself is never sent to the browser as a download:
* PDF  -> its bytes are embedded in the page and drawn page-by-page on
          canvases by PDF.js, so the browser's own PDF viewer (with its
          download/print buttons) never opens, even on Android/iPhone.
* DOCX -> converted to HTML on the server (mammoth) and shown in a sandboxed
          frame (no scripts can run).
* PNG/JPEG -> shown as an image.
* DOC (old Word) -> cannot be previewed; the page says so.

A person can still take a screenshot; this only removes the easy download.
"""
import base64
import re
from pathlib import Path

from django.http import Http404
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_BYTES = 6 * 1024 * 1024  # uploads are limited to 5 MB


def _docx_html(data):
    import io
    import mammoth
    result = mammoth.convert_to_html(io.BytesIO(data))
    html = result.value or ""
    # Only keep web links; drop javascript:/data: links that a document could carry.
    html = re.sub(r'href="(?!https?://|mailto:)[^"]*"', 'href="#"', html, flags=re.I)
    return html


def render_document(request, field, title, subtitle="", reupload_url=None):
    """Render the viewer page for a FileField, or 404 when there is no file."""
    if not field:
        raise Http404()
    try:
        with field.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except (FileNotFoundError, ValueError, OSError):
        raise Http404()
    if len(data) > MAX_BYTES:
        raise Http404()
    extension = Path(field.name).suffix.lower()
    context = {"title": title, "subtitle": subtitle, "kind": "unsupported", "reupload_url": reupload_url}
    if extension == ".pdf":
        context.update(kind="pdf", data_b64=base64.b64encode(data).decode("ascii"))
    elif extension == ".docx":
        try:
            context.update(kind="docx", docx_html=_docx_html(data))
        except Exception:  # damaged or unusual file
            context["kind"] = "unsupported"
    elif extension in IMAGE_TYPES:
        context.update(kind="image", image_src=f"data:{IMAGE_TYPES[extension]};base64,"
                       + base64.b64encode(data).decode("ascii"))
    back = request.META.get("HTTP_REFERER", "")
    if back and url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()},
                                                 require_https=request.is_secure()):
        context["back_url"] = back
    response = render(request, "pages/document_viewer.html", context)
    response["Cache-Control"] = "private, no-store"
    response["X-Frame-Options"] = "DENY"
    return response
