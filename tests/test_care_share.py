import unittest
from unittest.mock import Mock
from services.care_share import CareShare
from services.cloud import CloudError


class CareShareTests(unittest.TestCase):
    def test_invalid_invite_does_not_send_request(self):
        cloud = Mock()
        client = CareShare(cloud)
        for value in ('', 'not-a-code', '00000000-0000-1000-8000-000000000001', None):
            with self.assertRaisesRegex(CloudError, 'Revisa el código'):
                client.join(value, 'Familiar')
        cloud.request.assert_not_called()

    def test_pasted_invite_and_long_profile_are_accepted(self):
        cloud = Mock()
        cloud.request.return_value = {}
        code = '00000000-0000-4000-8000-000000000001'
        CareShare(cloud).join('  ' + code + '\n', 'Á' * 90)
        request = cloud.request.call_args
        self.assertEqual(request.args[2], dict(action='join', code=code, name='Á' * 60))
        self.assertTrue(request.kwargs['authorized'])
        self.assertNotIn('owner_id', request.args[2])


if __name__ == '__main__':
    unittest.main()
