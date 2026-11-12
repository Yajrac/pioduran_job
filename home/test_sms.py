from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from home.sms import format_ph_mobile, send_sms


def reply(status, body):
    response = Mock(status_code=status, text=str(body))
    response.json.return_value = body
    return response


@override_settings(DEBUG=False, SMS_PROVIDER='semaphore', SEMAPHORE_API_KEY='key123', SEMAPHORE_SENDER_NAME='')
class SemaphoreTests(SimpleTestCase):
    @patch('home.sms.requests.post', return_value=reply(200, [{'message_id': 1, 'status': 'Pending'}]))
    def test_sends_with_api_key_and_ph_number(self, post):
        self.assertTrue(send_sms('09171234567', 'Your code is 123456').ok)
        url, kwargs = post.call_args[0][0], post.call_args[1]
        self.assertEqual(url, 'https://api.semaphore.co/api/v4/messages')
        self.assertEqual(kwargs['data'], {'apikey': 'key123', 'number': '639171234567', 'message': 'Your code is 123456'})
        self.assertEqual(kwargs['timeout'], 15)

    @override_settings(SEMAPHORE_SENDER_NAME='PESOPIO')
    @patch('home.sms.requests.post', return_value=reply(200, [{'message_id': 1}]))
    def test_sender_name_is_optional(self, post):
        send_sms('09171234567', 'hi')
        self.assertEqual(post.call_args[1]['data']['sendername'], 'PESOPIO')

    @patch('home.sms.requests.post', return_value=reply(200, {'apikey': ['Invalid API key.']}))
    def test_error_object_is_a_failure(self, post):
        result = send_sms('09171234567', 'hi')
        self.assertFalse(result.ok)
        self.assertIn('Invalid API key', result.detail)

    @patch('home.sms.requests.post', side_effect=requests.ConnectionError('offline'))
    def test_network_error_does_not_crash(self, post):
        self.assertFalse(send_sms('09171234567', 'hi').ok)

    @override_settings(SEMAPHORE_API_KEY='')
    @patch('home.sms.requests.post')
    def test_missing_key_sends_nothing(self, post):
        self.assertFalse(send_sms('09171234567', 'hi').ok)
        post.assert_not_called()

    @override_settings(DEBUG=True, OTP_DEV_MODE=True)
    @patch('home.sms.requests.post')
    def test_dev_mode_prints_instead_of_sending(self, post):
        self.assertTrue(send_sms('09171234567', 'hi').ok)
        post.assert_not_called()

    @override_settings(SMS_PROVIDER='iprog', IPROG_SMS_API_TOKEN='tok')
    @patch('home.sms.requests.post', return_value=reply(200, {'status': 200}))
    def test_iprog_still_available(self, post):
        self.assertTrue(send_sms('09171234567', 'hi').ok)
        self.assertEqual(post.call_args[1]['json']['phone_number'], '639171234567')

    def test_format_ph_mobile(self):
        self.assertEqual(format_ph_mobile('0917-123 4567'), '639171234567')
        self.assertEqual(format_ph_mobile('+639171234567'), '639171234567')
