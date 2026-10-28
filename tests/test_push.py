import unittest
from unittest.mock import Mock, patch
from services.push import PushClient
from services.cloud import CloudError


class PushTests(unittest.TestCase):
    def client(self):
        cloud, mobile, bridge = Mock(), Mock(), Mock()
        cloud.user = {'id': 'owner'}
        mobile.configured = True
        mobile.native.return_value = (bridge, 'activity')
        mobile.initialize.return_value = bridge
        bridge.deviceId.return_value = '10000000-0000-4000-8000-000000000001'
        bridge.canNotify.return_value = True
        bridge.token.return_value = 'fixture-token'
        return PushClient(cloud, mobile), bridge

    def test_no_registration_without_permission_or_account(self):
        push, bridge = self.client()
        bridge.canNotify.return_value = False
        with self.assertRaises(CloudError): push.register()
        push.cloud.request.assert_not_called()
        push.cloud.user = None
        with self.assertRaises(CloudError): push.test()
        push.cloud.request.assert_not_called()

    def test_test_registers_current_token_then_sends_without_token_in_test_request(self):
        push, _ = self.client()
        push.test()
        calls = push.cloud.request.call_args_list
        self.assertEqual(calls[0].args[2]['action'], 'register')
        self.assertEqual(calls[1].args[2]['action'], 'test')
        self.assertNotIn('token', calls[1].args[2])
        self.assertTrue(all(call.kwargs['authorized'] for call in calls))

    @patch('services.push.time.sleep')
    def test_token_not_ready_never_registers_empty_value(self, sleep):
        push, bridge = self.client()
        bridge.token.return_value = ''
        with self.assertRaises(CloudError): push.register()
        push.cloud.request.assert_not_called()

    def test_unregister_works_after_permission_disabled(self):
        push, bridge = self.client()
        bridge.canNotify.return_value = False
        push.unregister()
        self.assertEqual(push.cloud.request.call_args.args[2]['action'], 'unregister')
