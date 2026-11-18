import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.premium import PremiumState


class PremiumStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'pets.premium.json'
        self.now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
        self.paid = '2026-12-17T12:00:00+00:00'
        self.result = dict(state='active', order_id='order-1', paid_until=self.paid)
        self.state = self.load()

    def load(self, owner='owner'):
        return PremiumState(self.path, owner, now=lambda: self.now)

    def test_new_order_celebrates_once_across_refresh_and_reload(self):
        self.assertFalse(self.state.active())
        self.assertTrue(self.state.record('luna', self.result))
        self.assertTrue(self.state.active())
        self.assertTrue(self.state.active('luna'))
        self.assertFalse(self.state.active('sol'))
        self.assertFalse(self.state.record('luna', self.result))
        restored = self.load()
        self.assertTrue(restored.active('luna'))
        self.assertFalse(restored.record('luna', self.result))

    def test_renewal_with_different_order_celebrates_once(self):
        self.state.record('luna', self.result)
        renewal = dict(self.result, order_id='order-2', paid_until='2027-01-17T12:00:00+00:00')
        self.assertTrue(self.state.record('luna', renewal))
        self.assertFalse(self.load().record('luna', renewal))
        self.now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(self.load().active('luna'))

    def test_background_refresh_does_not_consume_foreground_celebration(self):
        self.assertTrue(self.state.record('luna', self.result, acknowledge=False))
        self.assertTrue(self.load().active('luna'))
        self.assertTrue(self.load().record('luna', self.result))
        self.assertFalse(self.load().record('luna', self.result))

    def test_failed_checkout_preserves_previous_paid_time_without_celebration(self):
        self.state.record('luna', self.result)
        for state in ('pending', 'creating', 'rejected', 'cancelled'):
            self.assertFalse(self.state.record('luna', dict(state=state, order_id='failed', paid_until=None)))
            self.assertTrue(self.load().active('luna'))
        self.now = datetime(2026, 12, 17, 12, tzinfo=timezone.utc)
        self.assertFalse(self.state.active('luna'))
        self.assertFalse(self.load().active())

    def test_server_paid_time_restores_hint_even_if_latest_order_failed(self):
        self.assertFalse(self.state.record('luna', dict(self.result, state='rejected')))
        self.assertTrue(self.load().active('luna'))
        self.assertTrue(self.state.record('luna', self.result))

    def test_none_or_expired_without_validity_clears_hint_but_keeps_seen_order(self):
        for state in ('none', 'expired'):
            self.state.record('luna', self.result)
            self.assertFalse(self.state.record('luna', dict(state=state, paid_until=None)))
            self.assertFalse(self.load().active('luna'))
            self.assertFalse(self.state.record('luna', self.result))

    def test_owner_mismatch_and_guests_cannot_read_other_account_hint(self):
        self.state.record('luna', self.result)
        self.assertFalse(self.load('other').active())
        guest = self.load(None)
        self.assertFalse(guest.active())
        self.assertFalse(guest.record('luna', self.result))
        self.assertTrue(self.load().active())
        other = self.load('other')
        self.assertTrue(other.record('sol', self.result))
        self.assertFalse(other.active('luna'))
        self.assertFalse(self.load().active())

    def test_bad_cache_is_ignored_and_fresh_server_response_recovers(self):
        for contents in ('{', '[]', 'null', '42',
                         json.dumps({'owner': 'owner', 'pets': {'luna': self.paid}, 'seen': {}}),
                         json.dumps({'owner': 'owner', 'pets': {'luna': '2026-12-17T12:00:00'}, 'seen': []})):
            with self.subTest(contents=contents):
                self.path.write_text(contents, encoding='utf-8')
                restored = self.load()
                self.assertFalse(restored.active())
                self.assertTrue(restored.record('luna', self.result))
                self.assertTrue(self.load().active('luna'))

    def test_malformed_responses_never_grant_hint_or_celebration(self):
        for result in (None, [], 'active', {}, {'state': []},
                       dict(self.result, paid_until=None), dict(self.result, paid_until=[]),
                       dict(self.result, paid_until='2026-12-17T12:00:00'),
                       dict(self.result, paid_until='2026-11-17T12:00:00+00:00'),
                       dict(self.result, paid_until=self.now),
                       dict(self.result, state='invented')):
            with self.subTest(result=result):
                self.assertFalse(self.state.record('luna', result))
                self.assertFalse(self.state.active())
        for pet in (None, [], 1, '', ' '):
            self.assertFalse(self.state.record(pet, self.result))
            self.assertFalse(self.state.active(pet))

    def test_missing_order_never_celebrates_but_confirmed_date_can_show_badge(self):
        for order in (None, '', ' ', [], 42):
            self.assertFalse(self.state.record('luna', dict(self.result, order_id=order)))
        self.assertTrue(self.state.active('luna'))
        self.assertTrue(self.state.record('luna', self.result))

    def test_storage_failure_keeps_memory_and_does_not_repeat_celebration(self):
        self.state.record('sol', dict(self.result, order_id='sol-order'))
        with patch('services.premium.os.replace', side_effect=OSError('disk full')):
            self.assertTrue(self.state.record('luna', self.result))
            self.assertTrue(self.state.active('luna'))
            self.assertFalse(self.state.record('luna', self.result))
        self.assertTrue(self.load().active('sol'))
        self.assertFalse(self.load().active('luna'))
        self.state.record('luna', self.result)
        self.assertFalse(self.load().record('luna', self.result))

    def test_retain_pets_removes_deleted_pet_hint_without_replaying_its_order(self):
        self.state.record('luna', self.result)
        self.state.record('sol', dict(self.result, order_id='sol-order'))
        self.state.retain_pets(['sol'])
        self.assertFalse(self.load().active('luna'))
        self.assertTrue(self.load().active('sol'))
        self.assertFalse(self.load().record('luna', self.result))
