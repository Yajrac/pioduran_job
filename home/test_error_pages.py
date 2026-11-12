from types import SimpleNamespace

from django.test import SimpleTestCase, RequestFactory, override_settings
from django.urls import reverse

from .error_views import page_not_found
from .error_middleware import Friendly404Middleware
from django.http import HttpResponse


class NotFoundPageTests(SimpleTestCase):
    def test_anonymous_admin_and_portal_pages_redirect_to_valid_login(self):
        for path, login in [("/peso/applicants/", "/peso/"), ("/peso/dashboard/", "/peso/"), ("/my-applications/", "/login/")]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, login + "?next=" + path)

    def test_server_error_has_friendly_page_and_correct_status(self):
        middleware = Friendly404Middleware(lambda request: HttpResponse("Private traceback", status=500))
        response = middleware(RequestFactory().get("/broken/"))
        self.assertContains(response, "Something went wrong", status_code=500)
        self.assertNotContains(response, "Private traceback", status_code=500)

    def test_return_link_matches_authenticated_role(self):
        for role, route in [("admin", "peso-dashboard"), ("employer", "employer-dashboard"), ("applicant", "browse-job")]:
            with self.subTest(role=role):
                request = RequestFactory().get("/misspelled-page/")
                request.user = SimpleNamespace(is_authenticated=True, role=role)
                response = page_not_found(request)
                self.assertContains(response, f'href="{reverse(route)}"', status_code=404)

    def test_url_typos_show_custom_page_in_development_and_production(self):
        for debug in [True, False]:
            for path in ["/applicant/typo/", "/employer/typo/", "/peso/typo/", "/unknown-page/"]:
                with self.subTest(debug=debug, path=path), override_settings(DEBUG=debug):
                    response = self.client.get(path)
                    self.assertContains(response, "Page not found", status_code=404)
                    self.assertContains(response, "Back to Home", status_code=404)
                    self.assertNotContains(response, "URL patterns", status_code=404)
