from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from django.test import SimpleTestCase
from .hiring_analytics import hiring_analytics


class HiringAnalyticsTests(SimpleTestCase):
    def item(self, days, status='hired', job_id=1):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return SimpleNamespace(status=status, applied_at=start, hired_at=start + timedelta(days=days) if days is not None else None,
            job=SimpleNamespace(employer_id=1, job_id=job_id, company_name='Company', employer=SimpleNamespace(company_name='Company'), title='Role'), job_id=job_id)

    def test_elapsed_days_and_group_average(self):
        records = [self.item(1), self.item(3.5), self.item(10, job_id=2)]
        stats = hiring_analytics(records)
        self.assertEqual(stats['average_days'], 4.8)
        self.assertEqual(stats['measured_count'], 3)
        self.assertEqual(stats['breakdown'][0]['average_days'], 2.2)

    def test_missing_and_negative_dates_are_excluded(self):
        stats = hiring_analytics([self.item(None), self.item(-1), self.item(2, status='offered')])
        self.assertIsNone(stats['average_days'])
        self.assertEqual(stats['excluded_count'], 2)

    def test_same_day_is_valid_zero(self):
        stats = hiring_analytics([self.item(0)])
        self.assertEqual(stats['average_days'], 0)
        self.assertEqual(stats['measured_count'], 1)
