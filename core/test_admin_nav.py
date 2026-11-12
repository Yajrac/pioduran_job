from django.test import TestCase
from django.urls import reverse

from employer.models import Employer
from user.models import User


class AdminNavigationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('pesoadmin', first_name='Ana', last_name='Reyes', password='x', role='admin')
        owner = User.objects.create_user('company', password='x', role='employer')
        self.employer = Employer.objects.create(employer=owner, company_name='Acme', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d', approval_status='pending')
        self.client.force_login(self.admin)

    def test_detail_page_keeps_section_active_with_breadcrumb(self):
        response = self.client.get(reverse('employer_detail', args=[self.employer.pk]))
        self.assertEqual(response.context['admin_nav_section'], 'employers')
        self.assertContains(response, '<nav class="admin-breadcrumb" aria-label="Breadcrumb">', html=False)
        self.assertContains(response, f'<a href="{reverse("employer-list")}">Employers</a>', html=True)
        self.assertContains(response, '<span aria-current="page">Employer Profile</span>', html=True)

    def test_pending_count_skip_link_and_signed_in_name(self):
        response = self.client.get(reverse('peso-dashboard'))
        self.assertEqual(response.context['admin_pending_employers'], 1)
        self.assertContains(response, 'class="nav-count"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'Ana Reyes')
        self.assertNotContains(response, 'Admin Portal</strong>')

    def test_report_breadcrumb_names_the_section(self):
        response = self.client.get(reverse('reports'), {'section': 'demand'})
        self.assertEqual(response.context['admin_page_title'], 'Job Demand Ranking')

    def test_public_pages_get_no_admin_nav(self):
        response = self.client.get(reverse('home'))
        self.assertNotIn('admin_nav_section', response.context)

    def test_pending_employer_row_offers_review_instead_of_disabled_activate(self):
        response = self.client.get(reverse('employer-list'))
        self.assertContains(response, f'{reverse("employer_detail", args=[self.employer.pk])}#employerReviewForm')
        self.assertContains(response, 'btn-review')
        self.assertNotContains(response, 'approval required')
