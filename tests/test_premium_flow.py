from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from screens.billing import BillingFeatures
from screens.features import CareFeatures
from services.cloud import CloudError


class PremiumFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = BillingFeatures()
        self.flow.data_file = Path(self.tmp.name) / 'account.json'
        self.flow.cloud = Mock(user={'id': 'owner'}, configured=False)
        self.pet = {'id': 'pet', 'name': 'Jurel', 'kind': 'Gato', 'breed': 'Siamés'}
        self.flow.data = {'pets': [self.pet], 'qr_trials': {}, 'routines': [], 'events': []}
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

    def test_paid_pet_cannot_be_deleted_or_lose_its_care(self):
        self.flow.premium_state().record('pet', self.paid)
        self.flow.confirm = Mock()
        self.flow.message = Mock()
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.confirm.assert_not_called()
        self.assertEqual(self.flow.data['pets'], [self.pet])
        self.assertIn('01/12/2030', self.flow.message.call_args.args[1])

    def test_payment_confirmed_after_delete_prompt_still_prevents_removal(self):
        self.flow.confirm = Mock()
        self.flow.message = Mock()
        self.flow.save = Mock()
        self.flow.show = Mock()
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.premium_state().record('pet', self.paid)
        self.flow.confirm.call_args.args[2]()
        self.assertEqual(self.flow.data['pets'], [self.pet])
        self.flow.save.assert_not_called()

    def test_free_pet_can_still_be_deleted_offline(self):
        self.flow.confirm = Mock()
        self.flow.message = Mock()
        self.flow.save = Mock(return_value=True)
        self.flow.show = Mock()
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.confirm.call_args.args[2]()
        self.assertEqual(self.flow.data['pets'], [])

    def test_expired_paid_pet_can_be_deleted(self):
        self.flow.premium_state().record('pet', {**self.paid, 'paid_until': '2000-01-01T12:00:00+00:00'})
        self.test_free_pet_can_still_be_deleted_offline()

    def test_paid_plan_does_not_prevent_registering_another_pet(self):
        self.flow.premium_state().record('pet', self.paid)
        def form(title, fields, submit, **kwargs):
            submit({'name': 'Nube', 'kind': 'Gato', 'breed': 'Siamés'})
            return Mock(), {key: Mock(text=value) for key, _, value in fields}
        self.flow.form = form
        with patch('screens.features.PetFormPreview'):
            CareFeatures.register_pet(self.flow)
        self.assertEqual([pet['name'] for pet in self.flow.data['pets']], ['Jurel', 'Nube'])
        self.assertTrue(self.flow.premium_state().active('pet'))
        self.assertFalse(self.flow.premium_state().active(self.flow.data['pets'][1]['id']))

    def online_delete(self):
        self.flow.cloud.configured = True
        self.flow.confirm = Mock()
        self.flow.message = Mock()
        self.flow.save = Mock(return_value=True)
        self.flow.show = Mock()
        def network(operation, callback):
            try:
                result = operation()
            except CloudError as exc:
                self.flow.message('No se completó', str(exc))
                return
            callback(result)
        self.flow.network = network

    @patch('services.subscription.Subscription')
    @patch('services.public_qr.PublicChapas')
    def test_missing_cache_still_prevents_deleting_paid_pet(self, client, subscription):
        self.online_delete()
        client.return_value.existing.return_value = {'status': 'active', 'access_kind': 'paid'}
        subscription.return_value.call.return_value = self.paid
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.confirm.assert_not_called()
        self.assertEqual(self.flow.data['pets'], [self.pet])
        self.assertTrue(self.flow.premium_state().active('pet'))

    @patch('services.public_qr.PublicChapas')
    def test_unverified_account_plan_blocks_deletion_and_explains_connection(self, client):
        self.online_delete()
        client.return_value.existing.side_effect = CloudError('offline')
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.confirm.assert_not_called()
        self.flow.save.assert_not_called()
        self.assertIn('Conéctate', self.flow.message.call_args.args[1])

    def test_switched_account_ignores_pending_delete_check(self):
        self.online_delete()
        self.flow.network = Mock()
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.network.assert_called_once()
        checked = self.flow.network.call_args.args[1]
        self.flow.cloud.user = {'id': 'other'}
        checked(self.paid)
        self.flow.confirm.assert_not_called()
        self.assertEqual(self.flow.data['pets'], [self.pet])
        self.assertFalse(self.flow.premium_state().active('pet'))

    def test_switched_account_ignores_old_delete_confirmation(self):
        self.flow.confirm = Mock()
        self.flow.save = Mock()
        self.flow.show = Mock()
        CareFeatures.delete_pet(self.flow, self.pet)
        self.flow.cloud.user = {'id': 'other'}
        self.flow.confirm.call_args.args[2]()
        self.flow.save.assert_not_called()
        self.assertEqual(self.flow.data['pets'], [self.pet])

    @patch('services.subscription.Subscription')
    @patch('services.public_qr.PublicChapas')
    def test_verified_free_account_pet_can_be_deleted_with_or_without_qr(self, client, subscription):
        for tag in (None, {'status': 'expired'}):
            with self.subTest(tag=tag):
                self.flow.data['pets'] = [self.pet]
                self.online_delete()
                client.return_value.existing.return_value = tag
                subscription.return_value.call.return_value = {'state': 'none', 'paid_until': None}
                CareFeatures.delete_pet(self.flow, self.pet)
                self.flow.confirm.call_args.args[2]()
                self.assertEqual(self.flow.data['pets'], [])

    def test_guest_pet_can_be_deleted_without_connection(self):
        self.flow.cloud.user = None
        self.flow.cloud.configured = True
        self.test_free_pet_can_still_be_deleted_offline()

    @patch('services.public_qr.PublicChapas')
    def test_premium_without_web_qr_explains_prerequisite_without_starting_trial(self, client):
        client.return_value.existing.return_value = None
        self.flow.network = lambda operation, callback: callback(operation())
        modal, card = Mock(), Mock()
        self.flow.dialog = Mock(return_value=(modal, card))
        self.flow.show = Mock()
        self.flow.qr_info = Mock()
        with patch('screens.billing.view', side_effect=lambda name, **context: SimpleNamespace(name=name, context=context)), \
                patch('screens.billing.Subscription') as subscription:
            self.flow.open_subscription(self.pet)
        subscription.return_value.call.assert_not_called()
        self.assertIn('chapa', self.flow.dialog.call_args.args[0].lower())
        action = next(call.args[0] for call in card.add_widget.call_args_list
                      if call.args[0].name == 'AccountPrimary')
        action.context['callback']()
        self.flow.show.assert_called_once_with('Chapa')
        client.return_value.manage.assert_not_called()

    @patch('services.public_qr.PublicChapas')
    def test_missing_qr_cta_respects_an_already_used_account_trial(self, client):
        from screens.ux import UxFeatures
        client.return_value.existing.return_value = None
        client.return_value.trial_status.return_value = {
            'used': True, 'pet_id': 'previous-pet', 'pet_name': 'Anterior', 'status': 'unavailable'}
        self.flow.network = lambda operation, callback: callback(operation())
        self.flow.dialog = Mock(return_value=(Mock(), Mock()))
        self.flow.qr_owner = lambda: 'owner'
        self.flow.heading = Mock()
        self.flow.content = Mock()
        def show(page):
            self.flow.active = page
            UxFeatures.qr_page(self.flow)
        self.flow.show = show
        with patch('screens.ux.PublicChapas', client), \
                patch('screens.billing.view', side_effect=lambda name, **context: SimpleNamespace(name=name, context=context)), \
                patch('screens.ux.view', side_effect=lambda name, **context: SimpleNamespace(name=name, context=context)):
            self.flow.open_subscription(self.pet)
            card = self.flow.dialog.return_value[1]
            action = next(call.args[0] for call in card.add_widget.call_args_list
                          if call.args[0].name == 'AccountPrimary')
            action.context['callback']()
        texts = [call.args[0].context.get('text', '') for call in self.flow.content.add_widget.call_args_list]
        self.assertTrue(any('ya utilizó la prueba' in text for text in texts))
        self.assertFalse(any('Crear' in text for text in texts))
        client.return_value.manage.assert_not_called()

    @patch('services.public_qr.PublicChapas')
    def test_premium_with_existing_qr_queries_plan(self, client):
        client.return_value.existing.return_value = {'status': 'expired'}
        self.flow.network = lambda operation, callback: callback(operation())
        with patch('screens.billing.Subscription') as subscription:
            subscription.return_value.call.return_value = self.paid
            self.flow.open_subscription(self.pet)
        self.flow.payment_success.assert_called_once_with(self.pet, self.paid)

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
