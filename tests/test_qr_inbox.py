import unittest
from unittest.mock import Mock
from services.cloud import CloudError
from services.qr_inbox import QrInbox

THREAD = '00000000-0000-4000-8000-000000000001'
MESSAGE = '00000000-0000-4000-8000-000000000002'
REQUEST = '00000000-0000-4000-8000-000000000003'
DATE = '2026-10-07T20:00:00+00:00'


def conversation():
    return dict(id=THREAD, status='open', archived=False, expires_at=DATE, owner_read_at=None,
                pet_id='fixture-pet', pet_name='Luna', finder_name='Persona', finder_contact='', location_note='',
                messages=[dict(id=MESSAGE, sender='visitor', text='Encontré a Luna', created_at=DATE)])


class QrInboxTests(unittest.TestCase):
    def client(self):
        cloud = Mock(user={'id': THREAD})
        cloud.request.return_value = conversation()
        return QrInbox(cloud), cloud

    def test_account_required_and_identity_never_supplied_by_client(self):
        inbox, cloud = self.client()
        cloud.user = None
        with self.assertRaises(CloudError): inbox.list()
        cloud.request.assert_not_called()
        cloud.user = {'id': THREAD}
        cloud.request.return_value = {'unread': 1, 'threads': []}
        inbox.list()
        self.assertTrue(cloud.request.call_args.kwargs['authorized'])
        self.assertNotIn('owner_id', cloud.request.call_args.args[2])

    def test_read_does_not_acknowledge_or_write_to_cloud_backup(self):
        inbox, cloud = self.client()
        result = inbox.read(THREAD)
        self.assertEqual(result['messages'][0]['text'], 'Encontré a Luna')
        self.assertEqual(cloud.request.call_count, 1)
        self.assertEqual(cloud.request.call_args.args[2]['action'], 'read')
        inbox.mark_read(THREAD, MESSAGE)
        self.assertEqual(cloud.request.call_args.args[2]['message_id'], MESSAGE)

    def test_reply_retry_can_reuse_id_without_exposing_owner_phone(self):
        inbox, cloud = self.client()
        for _ in range(2): inbox.reply(THREAD, 'Gracias', REQUEST)
        payloads = [call.args[2] for call in cloud.request.call_args_list]
        self.assertEqual(payloads[0], payloads[1])
        self.assertNotIn('phone', payloads[0])

    def test_phone_mode_needs_new_explicit_confirmation(self):
        inbox, cloud = self.client()
        with self.assertRaises(CloudError): inbox.mode('pet', 'phone')
        cloud.request.assert_not_called()
        cloud.request.return_value = {'mode': 'phone'}
        inbox.mode('pet', 'phone', True)
        self.assertTrue(cloud.request.call_args.args[2]['confirm_phone'])

    def test_archive_is_separate_from_read_receipt_and_status(self):
        inbox, cloud = self.client()
        inbox.archive(THREAD)
        self.assertEqual(cloud.request.call_args.args[2], {'action': 'archive', 'thread_id': THREAD, 'archived': True})

    def test_invalid_or_unexpected_server_data_is_rejected(self):
        inbox, cloud = self.client()
        raw = conversation()
        raw['messages'][0]['text'] = 42
        cloud.request.return_value = raw
        with self.assertRaises(CloudError): inbox.read(THREAD)
        with self.assertRaises(CloudError): inbox.reply(THREAD, 'x' * 1001)
        with self.assertRaises(CloudError): inbox.mark_read('invalid', MESSAGE)


if __name__ == '__main__': unittest.main()
