import unittest
import json
from unittest.mock import Mock, patch
from services.cloud import Supabase, CloudError


class SessionTests(unittest.TestCase):
    def client(self):
        vault = Mock()
        cloud = Supabase(config_path='does-not-exist.json', session_storage=vault)
        cloud.url, cloud.key = 'https://example.supabase.co', 'sb_publishable_test'
        return cloud, vault

    def result(self, refresh='rotated'):
        return dict(access_token='access',refresh_token=refresh,expires_in=3600,user={'id':'fixture-user'})

    def cached(self, expires=0):
        return json.dumps(dict(url='https://example.supabase.co',access_token='access',refresh_token='previous',expires_at=expires,user={'id':'fixture-user'}))

    def test_signin_passes_session_to_native_encrypted_storage_not_a_local_file(self):
        cloud, vault = self.client()
        cloud.set_session(self.result())
        stored=json.loads(vault.write.call_args.args[0])
        self.assertEqual(stored['refresh_token'],'rotated')
        self.assertEqual(stored['access_token'],'access')
        self.assertNotIn('password', str(vault.write.call_args))

    def test_restart_refreshes_and_persists_rotated_token(self):
        cloud, vault = self.client()
        vault.read.return_value = self.cached()
        with patch.object(cloud, 'request', return_value=self.result()) as request:
            self.assertTrue(cloud.restore_session())
        request.assert_called_once_with('POST','/auth/v1/token?grant_type=refresh_token',{'refresh_token':'previous'})
        self.assertEqual(json.loads(vault.write.call_args.args[0])['refresh_token'],'rotated')

    def test_offline_preserves_saved_session_for_retry(self):
        cloud, vault = self.client()
        vault.read.return_value=self.cached()
        with patch.object(cloud, 'request', side_effect=CloudError('offline')):
            with self.assertRaises(CloudError): cloud.restore_session()
        vault.clear.assert_not_called()
        self.assertIsNotNone(cloud.user)

    def test_valid_cached_session_opens_without_network(self):
        cloud,vault=self.client()
        vault.read.return_value=self.cached(9999999999)
        with patch.object(cloud,'request') as request:
            self.assertTrue(cloud.restore_session())
        request.assert_not_called()

    def test_cache_for_another_project_is_not_used(self):
        cloud,vault=self.client()
        data=json.loads(self.cached());data['url']='https://other.supabase.co'
        vault.read.return_value=json.dumps(data)
        self.assertFalse(cloud.restore_session())
        self.assertIsNone(cloud.user)
        vault.clear.assert_called_once()

    def test_profile_edit_updates_cached_name_without_extending_session(self):
        cloud,vault=self.client()
        cloud.set_session(self.result())
        expires=cloud.session['expires_at']
        user={'id':'fixture-user','email':'fixture@example.invalid','user_metadata':{'contact_profile':{'name':'Nombre actualizado'}}}
        with patch.object(cloud,'request',return_value=user):
            cloud.update_profile({'name':'Nombre actualizado'})
        cached=json.loads(vault.write.call_args.args[0])
        self.assertEqual(cached['user']['user_metadata']['contact_profile']['name'],'Nombre actualizado')
        self.assertEqual(cached['expires_at'],expires)

    def test_expired_remote_session_clears_vault(self):
        cloud, vault = self.client()
        response=Mock(ok=False,status_code=400,text='invalid refresh token')
        response.json.return_value={'error':'invalid_grant'}
        with patch('services.cloud.requests.request',return_value=response):
            with self.assertRaises(CloudError): cloud.request('POST','/auth/v1/token?grant_type=refresh_token',{'refresh_token':'invalid'})
        vault.clear.assert_called_once()

    def test_logout_clears_even_when_offline(self):
        cloud, vault=self.client()
        cloud.set_session(self.result())
        with patch.object(cloud,'request',side_effect=CloudError('offline')):
            with self.assertRaises(CloudError): cloud.logout()
        self.assertIsNone(cloud.user)
        vault.clear.assert_called_once()


if __name__=='__main__': unittest.main()
