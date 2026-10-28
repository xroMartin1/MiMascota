"""Prueba de publicación explícita y conservación de revisión sin conexiones reales."""
import os
os.environ.setdefault('KIVY_NO_ARGS', '1')
import unittest
from unittest.mock import Mock, patch
from screens.public_tag import PublicTagFeatures
from services.cloud import CloudError
from services.store import empty_data, pet_values
from services.backup_sync import payload
from tempfile import TemporaryDirectory
from pathlib import Path


class Screen(PublicTagFeatures):
    def __init__(self):
        self.busy = False
        self.cloud = Mock(site_url='https://mascota.example')
        self.temp = TemporaryDirectory()
        self.data_file = Path(self.temp.name)/'account.json'
        self.data = empty_data()
        self.data['cloud_revision'] = 3
        self.data['pets'] = [dict(pet_values({'name':'Max', 'kind':'Perro'}), id='pet-a')]
        self.cloud.download.return_value = {'data': empty_data(), 'revision':3}
        self.confirm = Mock()
        self.save = Mock(return_value=True)
        self.public_tag_panel = Mock()
        self.message = Mock()
        self.require_account = Mock(return_value=True)

    def network(self, operation, callback):
        try:
            result = operation()
        except CloudError:
            return
        callback(result)


class PublicFlowTests(unittest.TestCase):
    @patch('screens.public_tag.PublicChapas')
    def test_issue_needs_confirmation_and_uploads_before_manage(self, client):
        screen = Screen()
        pet = screen.data['pets'][0]
        screen.cloud.upload.return_value = {'revision': 4}
        screen.publish_public_tag(pet, 'issue')
        screen.cloud.upload.assert_not_called()
        client.return_value.manage.assert_not_called()
        screen.confirm.call_args.args[2]()
        screen.cloud.upload.assert_called_once_with(dict(payload(screen.data), cloud_revision=3))
        client.return_value.manage.assert_called_once_with('pet-a', 'issue')
        self.assertEqual(screen.data['cloud_revision'], 4)

    @patch('screens.public_tag.PublicChapas')
    def test_failed_issue_keeps_uploaded_revision_and_does_not_show_qr(self, client):
        screen = Screen()
        screen.cloud.upload.return_value = {'revision': 4}
        client.return_value.manage.side_effect = CloudError('offline')
        screen.publish_public_tag(screen.data['pets'][0], 'issue')
        screen.confirm.call_args.args[2]()
        self.assertEqual(screen.data['cloud_revision'], 4)
        screen.save.assert_called_once()
        screen.public_tag_panel.assert_not_called()

    @patch('screens.public_tag.PublicChapas')
    def test_cloud_conflict_never_issues(self, client):
        screen = Screen()
        screen.cloud.upload.side_effect = CloudError('revision_conflict')
        screen.publish_public_tag(screen.data['pets'][0], 'issue')
        screen.confirm.call_args.args[2]()
        client.return_value.manage.assert_not_called()
        self.assertEqual(screen.data['cloud_revision'], 3)

    @patch('screens.public_tag.PublicChapas')
    def test_revoke_requires_confirmation_and_does_not_upload_local_changes(self, client):
        screen = Screen()
        screen.revoke_public_tag(screen.data['pets'][0])
        client.return_value.manage.assert_not_called()
        screen.confirm.call_args.args[2]()
        client.return_value.manage.assert_called_once_with('pet-a', 'revoke')
        screen.cloud.upload.assert_not_called()


if __name__ == '__main__':
    unittest.main()
