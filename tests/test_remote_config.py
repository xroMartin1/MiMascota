import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from services.cloud import CloudError
from services.remote_config import RemoteConfig, DEFAULT_TIP, TIP_PATH


class RemoteConfigTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'remote-config.json'
        self.cloud = Mock(url='https://example.supabase.co', configured=True)
        self.cloud.request.return_value = [{'message': 'Revisa el contacto de su chapa QR.', 'updated_at': '2026-10-28T12:00:00Z'}]

    def test_remote_value_survives_restart_offline(self):
        config = RemoteConfig(self.cloud, self.path)
        self.assertEqual(config.message, DEFAULT_TIP)
        self.assertTrue(config.refresh())
        self.cloud.request.assert_called_once_with('GET', TIP_PATH)
        self.assertEqual(config.source, 'remote')
        self.assertTrue(config.cache_saved)
        restored = RemoteConfig(self.cloud, self.path)
        self.cloud.request.side_effect = CloudError('Sin conexión')
        self.assertFalse(restored.refresh())
        self.assertEqual(restored.message, config.message)
        self.assertEqual(restored.source, 'cache')

    def test_malformed_payload_does_not_replace_cache(self):
        config = RemoteConfig(self.cloud, self.path)
        config.refresh()
        original = self.path.read_bytes()
        for bad in (None, {}, [], [{'message': ''}], [{'message': 'x'*201, 'updated_at': ''}],
                    [{'message': 'Texto\nno válido', 'updated_at': ''}]):
            self.cloud.request.return_value = bad
            self.assertFalse(config.refresh())
            self.assertEqual(self.path.read_bytes(), original)

    def test_corrupt_and_cross_project_cache_use_default(self):
        for content in ('[1]', 'broken', json.dumps({'origin': 'https://other.example','message': 'Otro proyecto'})):
            self.path.write_text(content, encoding='utf-8')
            config = RemoteConfig(self.cloud, self.path)
            self.assertEqual(config.message, DEFAULT_TIP)
            self.assertEqual(config.source, 'default')

    def test_without_config_does_not_request(self):
        self.cloud.configured = False
        self.assertFalse(RemoteConfig(self.cloud,self.path).refresh())
        self.cloud.request.assert_not_called()

    def test_disk_failure_still_displays_remote_tip(self):
        config = RemoteConfig(self.cloud,self.path)
        self.path.mkdir()
        self.assertTrue(config.refresh())
        self.assertEqual(config.source,'remote')
        self.assertFalse(config.cache_saved)


if __name__ == '__main__':
    unittest.main()
