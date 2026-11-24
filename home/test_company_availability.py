import json
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from .views import registration_company_check


class CompanyAvailabilityTests(SimpleTestCase):
    def test_duplicate_and_available_fields(self):
        for field, value in [('company_name', 'Testing'), ('contact_no', '09123456789')]:
            for exists in [True, False]:
                with self.subTest(field=field, exists=exists), patch('home.views.Employer.objects.filter') as query:
                    query.return_value.exists.return_value = exists
                    response = registration_company_check(RequestFactory().get('/', {'field': field, 'value': ' ' + value + ' '}))
                    data = json.loads(response.content)
                    self.assertEqual(data['available'], not exists)
                    query.assert_called_once_with(**{field + '__iexact': value})
                    self.assertEqual(response['Cache-Control'], 'no-store')

    def test_invalid_field_and_phone(self):
        for field, value in [('password', 'test'), ('business_permit_no', 'BPT-123'), ('contact_no', '123'), ('company_name', ''), ('company_name', '!!!')]:
            with self.subTest(field=field), patch('home.views.Employer.objects.filter') as query:
                response = registration_company_check(RequestFactory().get('/', {'field': field, 'value': value}))
                self.assertTrue(json.loads(response.content)['error'])
                query.assert_not_called()
