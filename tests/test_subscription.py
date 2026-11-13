import unittest
from unittest.mock import Mock
from services.subscription import Subscription
from services.cloud import CloudError

class SubscriptionTests(unittest.TestCase):
 def setUp(self):
  self.cloud=Mock(user={'id':'owner'})
  self.cloud.request.return_value={'test_mode':True,'amount':3990,'currency':'CLP','state':'pending','checkout_url':'https://www.mercadopago.cl/subscriptions/checkout?preapproval_id=fixture','paid_until':None}
 def test_only_server_state_and_hosted_checkout_are_used(self):
  result=Subscription(self.cloud).call('luna','create','buyer@testuser.com')
  self.assertEqual(result['state'],'pending')
  payload=self.cloud.request.call_args.args[2]
  self.assertNotIn('amount',payload)
  self.assertNotIn('owner_id',payload)
  self.assertTrue(self.cloud.request.call_args.kwargs['authorized'])
 def test_untrusted_mode_price_and_urls_are_rejected(self):
  for change in ({'test_mode':False},{'amount':1},{'checkout_url':'https://evil.example/checkout'},{'paid_until':'yesterday'}):
   base={'test_mode':True,'amount':3990,'currency':'CLP','state':'pending','checkout_url':None,'paid_until':None}
   self.cloud.request.return_value={**base,**change}
   with self.assertRaises(CloudError):Subscription(self.cloud).call('luna')
 def test_no_account_or_invalid_email_never_reaches_network(self):
  with self.assertRaises(ValueError):Subscription(self.cloud).call('luna','create','bad email')
  self.cloud.user=None
  with self.assertRaises(CloudError):Subscription(self.cloud).call('luna')
  self.cloud.request.assert_not_called()
