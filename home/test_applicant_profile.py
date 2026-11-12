from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applicant.models import Applicant
from employer.models import Employer, JobApplication, JobPost
from user.models import User


class ApplicantProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("miguel", "m@example.com", "x", role="applicant")
        self.applicant = Applicant.objects.create(user=self.user, first_name="Miguel", last_name="Base", middle_name="",
                                                  email="m@example.com", phone_number="09171234567",
                                                  skills="Sales, Cashiering, Inventory")
        owner = User.objects.create_user("store", "s@example.com", "x", role="employer")
        employer = Employer.objects.create(employer=owner, company_name="Sample Store", business_permit_no="BP-1",
                                           contact_no="09170000001", description="d")
        for title, status in [("Cashier", "pending"), ("Sales Clerk", "offered"), ("Bagger", "hired")]:
            job = JobPost.objects.create(employer=employer, title=title, description="d", qualifications="q",
                                         location="Pio Duran", deadline=timezone.localdate() + timedelta(days=9),
                                         status="approved")
            JobApplication.objects.create(job=job, applicant=self.applicant, status=status)
        self.client.force_login(self.user)

    def test_shows_summary_recent_applications_and_checklist(self):
        response = self.client.get(reverse("applicant-profile"))
        self.assertEqual(response.context["stats"], {"applied": 3, "in_review": 1, "offers": 1, "hired": 1})
        self.assertContains(response, "Sales Clerk")
        self.assertContains(response, "Sample Store")
        items = dict(response.context["profile_items"])
        self.assertTrue(items["At least 3 skills"])
        self.assertFalse(items["Resume uploaded"])
        self.assertContains(response, reverse("change-password"))

    def test_change_password_moves_out_of_the_applicant_header(self):
        response = self.client.get(reverse("browse-job"))
        self.assertNotContains(response, "Change Password</a>")


class StandaloneLoginPageTests(TestCase):
    def test_login_page_has_no_site_header_or_footer(self):
        response = self.client.get(reverse("login-user"))
        self.assertNotContains(response, 'class="site-header"')
        self.assertNotContains(response, 'class="site-footer')
        self.assertContains(response, "Back to home")

    def test_other_public_pages_keep_them(self):
        response = self.client.get(reverse("browse-job"))
        self.assertContains(response, 'class="site-header"')
        self.assertContains(response, 'class="site-footer')
