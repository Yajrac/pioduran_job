import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from applicant.models import Applicant
from employer.benchmarks import build_benchmarks
from employer.job_demand import demand_ranking
from employer.models import Employer, JobPost
from user.models import User

MEDIA = tempfile.mkdtemp()


@override_settings(DEBUG=True, MEDIA_ROOT=MEDIA)
class SeedDemoDataTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def test_seed_fills_every_screen_and_clear_keeps_real_accounts(self):
        real = User.objects.create_user("realperson", "real@example.com", "x", role="applicant")
        call_command("seed_demo_data", stdout=StringIO())

        self.assertEqual(Employer.objects.count(), 15)
        self.assertEqual(JobPost.objects.count(), 15)
        self.assertEqual(Applicant.objects.count(), 15)
        self.assertTrue(all("Pio Duran, Albay" in j.location for j in JobPost.objects.all()))
        self.assertTrue(User.objects.get(username="employer01").check_password("Testing@123"))
        sample = Applicant.objects.get(user__username="applicant01")
        self.assertTrue(sample.resume and sample.cover_letter and sample.profile_photo)

        benchmarks = build_benchmarks()
        self.assertTrue(benchmarks["sales_retail"]["ready"])
        self.assertTrue(benchmarks["food_service"]["ready"])
        self.assertFalse(benchmarks["office_admin"]["ready"])
        self.assertEqual(demand_ranking()[0]["category"], "sales_retail")

        call_command("seed_demo_data", stdout=StringIO())  # rerun is safe
        call_command("seed_demo_data", "--clear", stdout=StringIO())
        self.assertEqual(list(User.objects.values_list("username", flat=True)), [real.username])

    def test_does_not_take_over_a_real_username(self):
        User.objects.create_user("employer01", "owner@example.com", "x", role="employer")
        with self.assertRaises(CommandError):
            call_command("seed_demo_data", stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_refuses_without_debug_unless_forced(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_data")
