import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse
from services.cloud import Supabase, CloudError
from services.session_storage import SessionStorage
from services.google_auth import GoogleAuth
from services.backup_sync import payload, merge, synchronize, SyncConflict, SyncJournal
from services.store import empty_data, pet_values


def data(name='Luna', identity='pet-1'):
    value = empty_data()
    value['pets'] = [dict(pet_values(dict(name=name, kind='Gato')), id=identity)]
    return value


class PersistenceTests(unittest.TestCase):
    def client(self):
        storage = Mock()
        cloud = Supabase('missing.json', storage)
        cloud.url, cloud.key = 'https://fixture.supabase.co', 'sb_publishable_test'
        cloud.set_session(dict(access_token='fixture', refresh_token='current', user={'id':'fixture'}))
        return cloud, storage

    def test_transient_refresh_error_does_not_logout(self):
        cloud, storage = self.client()
        response = Mock(ok=False, status_code=400, text='temporary')
        response.json.return_value = {'code': 'unexpected_failure'}
        with patch('services.cloud.requests.request', return_value=response):
            with self.assertRaises(CloudError):
                cloud.request('POST', '/auth/v1/token?grant_type=refresh_token', {'refresh_token':'current'})
        self.assertIsNotNone(cloud.user)
        storage.clear.assert_not_called()

    def test_legacy_error_code_confirms_revoked_session(self):
        cloud, storage = self.client()
        response = Mock(ok=False, status_code=400, text='revoked')
        response.json.return_value = {'code':400, 'error_code':'refresh_token_not_found'}
        with patch('services.cloud.requests.request', return_value=response):
            with self.assertRaises(CloudError):
                cloud.request('POST', '/auth/v1/token?grant_type=refresh_token', {'refresh_token':'current'})
        self.assertIsNone(cloud.user)
        storage.clear.assert_called_once()

    def test_obsolete_refresh_response_does_not_clear_new_login(self):
        cloud, storage = self.client()
        response = Mock(ok=False, status_code=400, text='old token')
        response.json.return_value = {'code':'refresh_token_not_found'}
        with patch('services.cloud.requests.request', return_value=response):
            with self.assertRaises(CloudError):
                cloud.request('POST', '/auth/v1/token?grant_type=refresh_token', {'refresh_token':'old'})
        self.assertEqual(cloud.session['refresh_token'], 'current')
        storage.clear.assert_not_called()

    def test_persistence_failure_is_recorded_and_retried(self):
        cloud, storage = self.client()
        storage.write.return_value = False
        cloud.cache_session()
        self.assertFalse(cloud.session_persisted)
        storage.write.return_value = True
        cloud.retry_session_cache()
        self.assertTrue(cloud.session_persisted)

    def test_restore_does_not_replace_new_session(self):
        cloud, storage = self.client()
        self.assertTrue(cloud.restore_session())
        storage.read.assert_not_called()

    @unittest.skipUnless(sys.platform == 'win32', 'DPAPI requires Windows')
    def test_windows_cache_is_encrypted_and_survives_new_instance(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {'MIMASCOTA_DISABLE_SAVED_SESSION':'0'}):
            path = Path(folder)/'session.bin'
            first = SessionStorage(path=path)
            self.assertTrue(first.write('synthetic-token-only'))
            self.assertNotIn(b'synthetic-token-only', path.read_bytes())
            self.assertEqual(SessionStorage(path=path).read(), 'synthetic-token-only')
            first.clear()
            self.assertFalse(path.exists())


class MergeTests(unittest.TestCase):
    def test_new_device_loads_remote_without_erasing_it(self):
        cloud = Mock()
        cloud.download.return_value = {'data':data(), 'revision':4}
        result, revision = synchronize(cloud, empty_data(), None)
        self.assertEqual(result['pets'][0]['name'], 'Luna')
        self.assertEqual(revision, 4)
        cloud.upload.assert_not_called()

    def test_independent_changes_combine(self):
        base = payload(data())
        local, remote = payload(data()), payload(data())
        local['pets'][0]['name'] = 'Lunita'
        remote['pets'][0]['weight'] = '4.2'
        combined = merge(base, local, remote)
        self.assertEqual(combined['pets'][0]['name'], 'Lunita')
        self.assertEqual(combined['pets'][0]['weight'], '4.2')

    def test_conflicting_names_do_not_overwrite(self):
        with self.assertRaises(SyncConflict):
            merge(payload(data()), payload(data('Lunita')), payload(data('Luna nueva')))

    def test_deletion_survives_restart_journal(self):
        with TemporaryDirectory() as folder:
            journal = SyncJournal(Path(folder)/'account.json')
            journal.accept(data())
            base = SyncJournal(Path(folder)/'account.json').base
            self.assertEqual(merge(base, payload(empty_data()), payload(data()))['pets'], [])

    def test_delete_vs_edit_conflict_preserves_records(self):
        with self.assertRaises(SyncConflict):
            merge(payload(data()), payload(empty_data()), payload(data('Changed')))

    def test_upload_uses_remote_revision(self):
        cloud = Mock()
        cloud.download.return_value = {'data':data(), 'revision':7}
        cloud.upload.return_value = {'revision':8}
        _, revision = synchronize(cloud, data('Lunita'), payload(data()))
        self.assertEqual(cloud.upload.call_args.args[0]['cloud_revision'], 7)
        self.assertEqual(revision, 8)

    def test_edits_during_upload_are_retained(self):
        snapshot = payload(data())
        current = payload(data('Local edit'))
        accepted = payload(data())
        accepted['pets'][0]['weight'] = '3'
        combined = merge(snapshot, current, accepted)
        self.assertEqual(combined['pets'][0]['name'], 'Local edit')
        self.assertEqual(combined['pets'][0]['weight'], '3')


class RecoveryTests(unittest.TestCase):
    def storage(self):
        values = {}
        return Mock(read=lambda:values.get('data',''), write=lambda value:values.update(data=value) is None,
                    clear=lambda:values.clear())

    def test_pkce_survives_process_restart(self):
        cloud, storage = Mock(configured=True, url='https://fixture.supabase.co'), self.storage()
        first = GoogleAuth(cloud, storage)
        query = parse_qs(urlparse(first.begin()).query)
        restored = GoogleAuth(cloud, storage)
        self.assertTrue(restored.finish(query['redirect_to'][0] + '&code=synthetic'))
        self.assertEqual(restored.completed_flow, 'google')
        self.assertIsNone(restored.pending)

    def test_recovery_sends_challenge_not_verifier(self):
        cloud, storage = Mock(configured=True, url='https://fixture.supabase.co'), self.storage()
        auth = GoogleAuth(cloud, storage)
        auth.recover('fixture@example.invalid')
        method, path, body = cloud.request.call_args.args
        self.assertTrue(path.startswith('/auth/v1/recover?redirect_to='))
        self.assertEqual(body['code_challenge_method'], 's256')
        self.assertNotIn(auth.pending['verifier'], str(body))
        redirect = parse_qs(urlparse(path).query)['redirect_to'][0]
        restored = GoogleAuth(cloud, storage)
        restored.finish(redirect + '&code=synthetic')
        self.assertEqual(restored.completed_flow, 'recovery')

    def test_wrong_state_does_not_consume_pending_flow(self):
        cloud = Mock(configured=True, url='https://fixture.supabase.co')
        auth = GoogleAuth(cloud, self.storage())
        auth.begin()
        with self.assertRaises(CloudError):
            auth.finish('mimascota://auth/callback?state=wrong&code=synthetic')
        self.assertIsNotNone(auth.pending)
        cloud.request.assert_not_called()
