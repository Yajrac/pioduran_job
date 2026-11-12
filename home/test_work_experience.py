from django.test import TestCase
from django.urls import reverse
from user.models import User
from applicant.models import Applicant, WorkExperience
from .experience_forms import WorkExperienceForm


class WorkExperienceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='candidate')
        self.applicant = Applicant.objects.create(user=self.user, email='candidate@example.com')
        self.client.force_login(self.user)
        self.data = {'job_title':'Cashier', 'company':'Sample Store', 'start_date':'2024-01-01', 'end_date':'2025-01-01', 'description':'Customer service and inventory.'}

    def test_add_edit_delete_and_profile_render(self):
        response = self.client.post(reverse('add-work-experience'), self.data)
        self.assertRedirects(response, reverse('applicant-profile'))
        item = WorkExperience.objects.get()
        self.assertEqual(item.applicant, self.applicant)
        page = self.client.get(reverse('applicant-profile'))
        self.assertContains(page, 'Cashier')
        self.assertEqual(page.content.count(b'id="experienceDeleteDialog"'), 1)
        response = self.client.post(reverse('edit-work-experience', args=[item.pk]), {**self.data, 'job_title':'Sales Assistant'})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.job_title, 'Sales Assistant')
        url = reverse('delete-work-experience', args=[item.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(WorkExperience.objects.exists())

    def test_current_job_has_no_end_date(self):
        form = WorkExperienceForm({**self.data, 'is_current':True})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['end_date'])

    def test_invalid_dates_are_rejected(self):
        for changes in [{'end_date':'2023-01-01'}, {'start_date':'2099-01-01'}, {'end_date':''}, {'end_date':'2099-01-01'}]:
            with self.subTest(changes=changes):
                self.assertFalse(WorkExperienceForm({**self.data, **changes}).is_valid())

    def test_other_user_cannot_edit_or_delete(self):
        self.client.post(reverse('add-work-experience'), self.data)
        item = WorkExperience.objects.get()
        stranger = User.objects.create_user(username='other')
        Applicant.objects.create(user=stranger, email='other@example.com')
        self.client.force_login(stranger)
        for name in ['edit-work-experience', 'delete-work-experience']:
            self.assertEqual(self.client.post(reverse(name, args=[item.pk]), self.data).status_code, 404)
        self.assertTrue(WorkExperience.objects.filter(pk=item.pk).exists())
