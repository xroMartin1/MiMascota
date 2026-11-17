import unittest
from unittest.mock import Mock
from services.subscription import Subscription
from services.cloud import CloudError


class SubscriptionTests(unittest.TestCase):
    def test_real_server_uuid_hmac_capability_contract(self):
        capability = '11111111-1111-4111-8111-111111111111.' + 'a' * 64
        url = 'https://mi-mascota-web.vercel.app/pago/webpay?checkout=' + capability
        self.assertEqual(Subscription(self.cloud).validate_checkout(url), url)

    def setUp(self):
        self.cloud = Mock(user={'id': 'owner'}, site_url='https://mi-mascota-web.vercel.app')
        self.base = dict(provider='webpay', test_mode=True, amount=3990, currency='CLP',
                         state='pending', checkout_url='https://mi-mascota-web.vercel.app/pago/webpay?checkout=11111111-1111-4111-8111-111111111111.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                         paid_until=None, order_id='order-123')
        self.cloud.request.return_value = self.base.copy()

    def test_authenticated_create_sends_only_pet_and_action(self):
        result = Subscription(self.cloud).call('luna', 'create')
        self.assertEqual(result['state'], 'pending')
        self.cloud.request.assert_called_once_with('POST', '/functions/v1/webpay-payments',
            {'pet_id': 'luna', 'action': 'create'}, authorized=True)

    def test_invalid_request_never_reaches_network(self):
        for pet, action in [(None, 'status'), ('', 'status'), (' ', 'status'), ([], 'status'),
                            ('luna', 'cancel'), ('luna', []), ('luna', None)]:
            with self.subTest(pet=pet, action=action), self.assertRaises(ValueError):
                Subscription(self.cloud).call(pet, action)
        self.cloud.user = None
        with self.assertRaises(CloudError):
            Subscription(self.cloud).call('luna')
        self.cloud.request.assert_not_called()

    def test_untrusted_contract_values_are_rejected(self):
        for change in [{'provider': 'mercadopago'}, {'provider': None}, {'test_mode': 1},
                       {'amount': 3990.0}, {'amount': '3990'}, {'amount': True}, {'currency': 'USD'},
                       {'state': []}, {'state': 'authorized'}, {'state': None}, {'paid_until': []},
                       {'paid_until': ''}, {'paid_until': '2026-11-17'}, {'paid_until': 'yesterday'},
                       {'order_id': []}, {'order_id': ''}, {'order_id': 'secret\nvalue'},
                       {'checkout_url': []}, {'checkout_url': ''}]:
            with self.subTest(change=change):
                self.cloud.request.return_value = {**self.base, **change}
                with self.assertRaises(CloudError):
                    Subscription(self.cloud).call('luna')
        for malformed in (None, [], 'ok'):
            self.cloud.request.return_value = malformed
            with self.assertRaises(CloudError):
                Subscription(self.cloud).call('luna')

    def test_only_exact_own_checkout_capability_url_is_openable(self):
        origin = 'https://mi-mascota-web.vercel.app'
        for url in ['http://mi-mascota-web.vercel.app/pago/webpay?checkout=x',
                    'https://evil.example/pago/webpay?checkout=x',
                    origin + '.evil.example/pago/webpay?checkout=x',
                    'https://user@mi-mascota-web.vercel.app/pago/webpay?checkout=x',
                    origin + ':443/pago/webpay?checkout=x', origin + ':bad/pago/webpay?checkout=x',
                    origin + '/pago/webpay/?checkout=x', origin + '/pago/webpay?checkout=',
                    origin + '/pago/webpay?checkout=x&checkout=y', origin + '/pago/webpay?checkout=x&token_ws=y',
                    origin + '/pago/webpay?checkout=x&access_token=firebase', origin + '/pago/webpay?checkout=x#token',
                    origin + '/pago/webpay?checkout=https%3A%2F%2Fevil.example',
                    origin + '/pago/webpay?checkout=x%0ay', origin + '/pago/webpay?checkout=eyJ.a.b',
                    origin + '/pago/webpay?checkout=x\n']:
            with self.subTest(url=url):
                self.cloud.request.return_value = {**self.base, 'checkout_url': url}
                with self.assertRaises(CloudError):
                    Subscription(self.cloud).call('luna')

    def test_configured_origin_and_all_server_states_preserve_paid_date(self):
        self.cloud.site_url = 'https://premium.example/'
        for state in ('none', 'creating', 'pending', 'active', 'rejected', 'cancelled', 'expired'):
            self.cloud.request.return_value = {**self.base, 'state': state,
                'checkout_url': 'https://premium.example/pago/webpay?checkout=11111111-1111-4111-8111-111111111111.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'paid_until': '2026-12-17T12:00:00+00:00'}
            self.assertEqual(Subscription(self.cloud).call('luna')['paid_until'], '2026-12-17T12:00:00+00:00')

    def test_null_optional_fields_are_valid(self):
        self.cloud.request.return_value = {**self.base, 'state': 'none', 'checkout_url': None, 'order_id': None}
        self.assertEqual(Subscription(self.cloud).call('luna')['state'], 'none')
