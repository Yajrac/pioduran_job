"""
URL configuration for job_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
import posixpath

from django.http import Http404
from django.urls import re_path
from django.views.static import serve

# Personal documents are served only through access-checked views.
PRIVATE_MEDIA = ("resume/", "cover/", "job_applications/")


def public_media(request, path):
    normalized = posixpath.normpath("/" + path.replace("\\", "/")).lstrip("/").lower()
    if normalized.startswith(PRIVATE_MEDIA):
        raise Http404()
    return serve(request, path, document_root=settings.MEDIA_ROOT)


handler404 = "home.error_views.page_not_found"
handler500 = "home.error_views.server_error"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('peso/', include('core.urls')),
    path('', include('home.urls'))
]
if settings.DEBUG:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", public_media)]
