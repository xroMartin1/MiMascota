import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse
from services.google_auth import GoogleAuth, CALLBACK
from services.cloud import CloudError
from services.mobile import MobileServices
from tools.configure_firebase import parse_config


class MobileAuthTests(unittest.TestCase):
    def test_google_uses_pkce_and_never_puts_verifier_in_url(self):
        cloud = Mock(configured=True, url='https://example.supabase.co')
        auth = GoogleAuth(cloud)
        query = parse_qs(urlparse(auth.begin()).query)
        self.assertEqual(query['provider'], ['google'])
        self.assertEqual(query['code_challenge_method'], ['s256'])
        self.assertNotIn(auth.pending['verifier'], str(query))
        redirect = query['redirect_to'][0]
        auth.finish(redirect + '&code=test-code')
        cloud.request.assert_called_once_with('POST', '/auth/v1/token?grant_type=pkce',
                                             {'auth_code': 'test-code', 'code_verifier': unittest.mock.ANY})
        cloud.set_session.assert_called_once()
        self.assertIsNone(auth.pending)
        with self.assertRaises(CloudError): auth.finish(redirect + '&code=test-code')

    def test_google_rejects_wrong_state_and_expired_callback(self):
        for callback in ('mimascota://auth/callback?state=wrong&code=x', 'https://evil.example/?code=x'):
            cloud = Mock(configured=True, url='https://example.supabase.co')
            auth = GoogleAuth(cloud)
            auth.begin()
            with self.assertRaises(CloudError): auth.finish(callback)
            cloud.request.assert_not_called()
        auth.begin()
        state = auth.pending['state']
        auth.pending['deadline'] = 0
        with self.assertRaises(CloudError): auth.finish(CALLBACK + '?state=' + state + '&code=x')

    def test_firebase_rejects_server_credentials_and_other_android_package(self):
        with self.assertRaises(ValueError): parse_config({'type': 'service_account', 'private_key': 'never-use'})
        data = {'project_info': {'project_id': 'test', 'project_number': '123'}, 'client': []}
        with self.assertRaises(ValueError): parse_config(data)
        data['client'] = [{'client_info': {'mobilesdk_app_id': '1:123:android:example',
                                          'android_client_info': {'package_name': 'org.mimascota.mimascota'}},
                           'api_key': [{'current_key': 'public-test'}]}]
        self.assertEqual(parse_config(data)['sender_id'], '123')

    @patch('services.mobile.platform', 'android')
    def test_optional_sdks_are_not_started_without_config(self):
        mobile = MobileServices({})
        mobile.native = Mock()
        mobile.configure(True, True)
        mobile.screen('Inicio')
        self.assertEqual(mobile.preferences(), {'notifications': False, 'analytics': False})
        mobile.native.assert_not_called()


if __name__ == '__main__': unittest.main()
