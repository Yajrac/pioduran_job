from types import SimpleNamespace
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from user.models import User
from applicant.models import Applicant
from .skill_extraction import detect_skills, experience_matches
from .skill_review import SkillReviewForm
from .views import get_job_recommendation


class SkillReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reviewer')
        self.applicant = Applicant.objects.create(user=self.user, email='reviewer@example.com', resume='resume/test.pdf', skills='Cooking')
        self.client.force_login(self.user)

    def test_aliases_and_word_boundaries(self):
        self.assertIn('Cashiering', detect_skills('I worked as a cashier.'))
        self.assertIn('Inventory Management', detect_skills('inventory records'))
        self.assertNotIn('SQL', detect_skills('MySQL database'))

    def test_get_never_saves_suggestions_and_post_saves_only_selected(self):
        with patch('django.db.models.fields.files.FieldFile.open'), patch('home.skill_review.extract_resume_text', return_value='customer service and inventory'):
            response = self.client.get(reverse('review-resume-skills'))
            self.assertContains(response, 'Customer Service')
            self.assertContains(response, '<main class="portal-main">')
            self.assertNotContains(response, '<main class="hero-section">')
            self.applicant.refresh_from_db()
            self.assertEqual(self.applicant.skills, 'Cooking')
            response = self.client.post(reverse('review-resume-skills'), {'skills':'Cooking', 'suggested':['Customer Service']})
            self.assertEqual(response.status_code, 302)
            self.applicant.refresh_from_db()
            self.assertEqual(self.applicant.skills, 'Cooking, Customer Service')

    def test_forged_suggestion_is_rejected(self):
        form = SkillReviewForm({'skills':'Cooking', 'suggested':['Unlisted']}, suggestions=['Sales'])
        self.assertFalse(form.is_valid())

    def test_skills_are_deduplicated(self):
        form = SkillReviewForm({'skills':'Sales, sales', 'suggested':['Sales']}, suggestions=['Sales'])
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['confirmed_skills'], 'Sales')

    def test_experience_matching_and_skill_synonyms(self):
        job = SimpleNamespace(title='Store Cashier', description='Manage inventory and assist customers.', qualifications='', responsibilities='', location='Albay')
        match = experience_matches(job, [SimpleNamespace(job_title='Store Assistant', company='Shop', description='Managed inventory')])
        self.assertEqual(match, ['Store Assistant at Shop'])
        score, skills = get_job_recommendation(job, 'Cashiering')
        self.assertEqual(score, 100)
        self.assertTrue(skills)

    def test_no_resume_allows_manual_skills(self):
        self.applicant.resume = ''
        self.applicant.save()
        response = self.client.post(reverse('review-resume-skills'), {'skills':'Customer Service'})
        self.assertEqual(response.status_code, 302)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.skills, 'Customer Service')
