from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from screens.billing import BillingFeatures


class PremiumFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = BillingFeatures()
        self.flow.data_file = Path(self.tmp.name) / 'account.json'
        self.flow.cloud = Mock(user={'id': 'owner'}, configured=False)
        self.pet = {'id': 'pet', 'name': 'Jurel', 'kind': 'Gato', 'breed': 'Siamés'}
        self.flow.data = {'pets': [self.pet]}
        self.flow.shell = Mock()
        self.flow.payment_success = Mock()
        self.flow.render_subscription = Mock()
        self.paid = {'state': 'active', 'order_id': 'order-1', 'paid_until': '2030-12-01T12:00:00+00:00'}

    def test_confirmed_payment_celebrates_once_and_updates_profile(self):
        self.flow.accept_premium_result(self.pet, self.paid)
        self.flow.payment_success.assert_called_once()
        self.assertTrue(self.flow.shell.ids.account.premium)
        self.flow.accept_premium_result(self.pet, self.paid)
        self.flow.payment_success.assert_called_once()
        self.flow.render_subscription.assert_called_once_with(self.pet, self.paid)

    def test_background_hint_does_not_consume_payment_confirmation(self):
        self.flow.premium_state().record('pet', self.paid, acknowledge=False)
        self.flow.accept_premium_result(self.pet, self.paid)
        self.flow.payment_success.assert_called_once()

    def test_pending_and_rejected_never_show_success(self):
        for state in ('pending', 'creating', 'rejected', 'cancelled', 'expired', 'none'):
            self.flow.accept_premium_result(self.pet, {**self.paid, 'state': state})
        self.flow.payment_success.assert_not_called()

    def test_owner_switch_clears_badge_and_never_reuses_other_cache(self):
        self.flow.accept_premium_result(self.pet, self.paid)
        self.flow.cloud.user = {'id': 'other'}
        self.flow.update_premium_badge()
        self.assertFalse(self.flow.shell.ids.account.premium)
        self.flow.cloud.user = None
        self.flow.update_premium_badge()
        self.assertFalse(self.flow.shell.ids.account.premium)

    def test_removing_paid_pet_clears_profile_hint(self):
        self.flow.accept_premium_result(self.pet, self.paid)
        self.flow.data['pets'] = []
        self.flow.update_premium_badge()
        self.assertFalse(self.flow.shell.ids.account.premium)

    def test_older_background_response_cannot_clear_a_new_confirmed_payment(self):
        self.flow.cloud.configured = True
        with patch('threading.Thread', side_effect=lambda target, **_: SimpleNamespace(start=target)), \
                patch('kivy.clock.Clock.schedule_once') as later, patch('screens.billing.Subscription') as subscription:
            subscription.return_value.call.return_value = {'state': 'none', 'paid_until': None}
            self.flow.refresh_premium_badge(force=True)
            finish_background = later.call_args.args[0]
        self.flow.accept_premium_result(self.pet, self.paid)
        finish_background(0)
        self.assertTrue(self.flow.shell.ids.account.premium)

    def test_desktop_return_from_checkout_checks_open_payment(self):
        from main import MiMascotaApp
        self.flow.refresh_subscription = Mock()
        app = SimpleNamespace(root=Mock())
        app.root.get_screen.return_value = self.flow
        MiMascotaApp.premium_focus(app, None, False)
        self.flow.refresh_subscription.assert_not_called()
        MiMascotaApp.premium_focus(app, None, True)
        self.flow.refresh_subscription.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
