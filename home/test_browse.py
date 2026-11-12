from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.templatetags.admin_format import posted_ago
from employer.models import Employer, JobPost
from user.models import User


class BrowseJobsTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('company', password='x', role='employer')
        self.employer = Employer.objects.create(employer=owner, company_name='Acme', business_permit_no='BP-1',
                                                contact_no='09170000001', description='d')
        today = timezone.localdate()
        common = dict(employer=self.employer, description='d', qualifications='q', location='Pio Duran', status='approved')
        JobPost.objects.create(title='Cashier', category='sales_retail', deadline=today + timedelta(days=3), salary=12000, **common)
        JobPost.objects.create(title='Cook', category='food_service', job_type='part_time', deadline=today + timedelta(days=30), **common)
        JobPost.objects.create(title='Hidden', category='other', deadline=today, **{**common, 'status': 'pending'})

    def test_filters_and_cards(self):
        response = self.client.get(reverse('browse-job'))
        filters = response.context['browse_filters']
        self.assertEqual(sorted(label for (key, label), n in filters['categories']), ['Food Service', 'Sales & Retail'])
        self.assertEqual(sorted(label for (key, label), n in filters['types']), ['Full Time', 'Part Time'])
        self.assertEqual(filters['employers'], [('Acme', 2)])
        self.assertContains(response, 'Closes in 3 days')
        self.assertContains(response, 'data-category="food_service"')
        self.assertNotContains(response, 'Hidden')

    def test_posted_ago(self):
        now = timezone.now()
        self.assertEqual(posted_ago(now), 'today')
        self.assertEqual(posted_ago(now - timedelta(days=1)), 'yesterday')
        self.assertEqual(posted_ago(now - timedelta(days=4)), '4 days ago')
        self.assertEqual(posted_ago(now - timedelta(days=15)), '2 weeks ago')
        self.assertEqual(posted_ago(now - timedelta(days=65)), '2 months ago')
