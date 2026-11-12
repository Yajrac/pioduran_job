from types import SimpleNamespace
from django.test import SimpleTestCase
from .candidate_ranking import candidate_match, parse_required_skills, ranking_requirements_error


class CandidateRankingTests(SimpleTestCase):
    def job(self, required='Customer Service, Inventory Management, Cashiering, Driving', experience=True):
        return SimpleNamespace(required_skills=required, experience_required=experience, title='Store Assistant', description='', qualifications='', responsibilities='')

    def experience(self):
        return SimpleNamespace(job_title='Store Assistant', company='Shop', description='Inventory and cashiering')

    def test_three_of_four_skills_plus_experience_scores_eighty(self):
        result = candidate_match(self.job(), ['Customer Service','Inventory Management','Cashiering'], [self.experience()])
        self.assertEqual(result['score'], 80)
        self.assertEqual(result['skills_points'], 60)
        self.assertEqual(result['experience_points'], 20)
        self.assertEqual(result['missing'], ['Driving'])

    def test_extra_skills_never_penalize_coverage(self):
        result = candidate_match(self.job('Cashiering', False), ['Cashiering','Cooking','Python'], [])
        self.assertEqual(result['score'], 100)

    def test_no_required_experience_means_skills_only(self):
        result = candidate_match(self.job(experience=False), ['Customer Service','Cashiering'], [])
        self.assertEqual(result['score'], 50)

    def test_missing_requirements_have_no_score(self):
        self.assertIsNone(candidate_match(self.job(''), ['Python'], [])['score'])

    def test_no_experience_cannot_get_experience_points(self):
        result = candidate_match(self.job('Cashiering'), ['Cashiering'], [])
        self.assertEqual(result['score'], 80)

    def test_duplicate_requirements_and_limits(self):
        self.assertEqual(parse_required_skills('Sales, sales,  Cooking '), ['Sales','Cooking'])
        self.assertTrue(ranking_requirements_error(','.join(f'Skill {i}' for i in range(21))))
        self.assertTrue(ranking_requirements_error('123'))

    def test_synonyms_and_whole_words(self):
        self.assertEqual(candidate_match(self.job('Cashiering', False), ['Cashier'], [])['score'], 100)
        self.assertEqual(candidate_match(self.job('Java', False), ['JavaScript'], [])['score'], 0)
