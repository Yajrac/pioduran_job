from django.conf import settings
from .error_views import page_not_found, server_error


class Friendly404Middleware:
    """Also show the public 404 design during local development."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 500 and response.get("Content-Type", "").startswith("text/html"):
            return server_error(request)
        if settings.DEBUG and response.status_code == 404 and response.get("Content-Type", "").startswith("text/html"):
            return page_not_found(request)
        return response
