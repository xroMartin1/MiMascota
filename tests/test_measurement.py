import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from services.measurement import Measurement, valid_event


class MeasurementTests(unittest.TestCase):
    def test_sdk_reserved_error_name_is_not_a_custom_event(self):
        self.assertFalse(valid_event('error', {'code': 'storage'}))
        self.assertTrue(valid_event('usage_error', {'code': 'storage'}))

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'evaluation.json'
        self.now = datetime(2026, 11, 1, 0, tzinfo=timezone.utc)
        self.clock = patch('services.measurement.utcnow', side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.sender = Mock()
        self.m = Measurement(self.path, self.sender)

    def data(self, due='2026-11-01 12:00', repeat='Diaria'):
        return {'routines': [{'id': 'private-task', 'due_at': due, 'repeat': repeat, 'done': False,
                              'title': 'Sensitive name', 'pet': 'private-pet'}],
                'reminder_settings': {'enabled': True, 'timezone': 'UTC'}}

    def test_opt_in_revocation_and_private_schema(self):
        self.m.event('pet_saved')
        self.m.observe(self.data())
        self.assertFalse(self.path.exists())
        self.m.configure(True, self.data())
        self.assertFalse(self.m.event('pet_saved', email='private@example.com'))
        self.assertFalse(self.m.event('unknown'))
        self.assertTrue(self.m.event('pet_saved'))
        self.assertNotIn('private', self.path.read_text())
        self.assertNotIn('Sensitive', self.path.read_text())
        self.sender.assert_called_once_with('pet_saved', {})
        self.m.configure(False)
        self.assertFalse(self.path.exists())

    def test_recurrence_skips_undo_and_reload(self):
        self.m.configure(True, self.data())
        self.now += timedelta(days=3, hours=14)
        self.m.care_completed('private-task', '2026-11-01 12:00')
        self.m.observe(self.data('2026-11-05 12:00'))
        self.m = Measurement(self.path)
        self.m.configure(True, self.data('2026-11-05 12:00'))
        result = self.m.summary('2026-11-01T00:00:00Z', '2026-11-05T00:00:00Z')['care']
        self.assertEqual((result['eligible'], result['completed'], result['late']), (4, 1, 1))
        self.m.care_completed('private-task', '2026-11-01 12:00', undo=True)
        self.assertEqual(self.m.summary(self.now - timedelta(days=4), self.now)['care']['completed'], 0)

    def test_cancel_preserves_overdue_but_excludes_future_and_no_history(self):
        self.now += timedelta(hours=13)
        self.m.configure(True, self.data())
        self.now += timedelta(days=2)
        self.m.observe({'routines': []})
        care = self.m.summary(self.now - timedelta(days=4), self.now + timedelta(days=4))['care']
        self.assertEqual(care['eligible'], 2)
        self.assertIsNone(Measurement(Path(self.tmp.name) / 'empty').summary(self.now, self.now)['care']['rate'])

    def test_active_idle_and_background_are_monotonic(self):
        with patch('services.measurement.monotonic', return_value=0) as mono:
            self.m.configure(True)
            self.m.screen('Inicio')
            mono.return_value = 45
            self.now += timedelta(seconds=45)
            self.m.touch()
            mono.return_value = 50
            self.now += timedelta(seconds=5)
            self.m.pause()
            mono.return_value = 500
            self.now += timedelta(seconds=450)
            self.m.resume()
            mono.return_value = 510
            self.now += timedelta(seconds=10)
            self.m.pause()
        result = self.m.summary(self.now - timedelta(days=1), self.now)
        self.assertEqual((result['active_seconds'], result['idle_seconds'], result['interactions']), (45, 15, 1))

    def test_retention_export_and_failures(self):
        self.m.configure(True)
        self.m.event('pet_saved')
        self.now += timedelta(days=31)
        self.sender.side_effect = RuntimeError('offline')
        self.assertTrue(self.m.event('pet_saved'))
        out = Path(self.tmp.name) / 'export.json'
        self.assertTrue(self.m.export(out))
        rows = json.loads(out.read_text())['events']
        self.assertEqual(len(rows), 1)
        with patch('services.measurement.os.replace', side_effect=OSError('full')):
            self.assertFalse(self.m.event('pet_saved'))

    def test_explicit_participants_activation_and_attempt_denominator(self):
        self.m.configure(True)
        participant = self.m.enroll()
        self.assertEqual(len(participant), 32)
        self.m.event('pet_saved')
        self.m.event('pet_saved')
        self.m.event('save_attempt', operation='pet')
        self.m.event('save_result', operation='pet', result='success')
        self.m.event('save_result', operation='pet', result='validation')
        result = self.m.summary(self.now - timedelta(seconds=1), self.now + timedelta(seconds=1))
        self.assertEqual(result['activation'], {'eligible': 1, 'activated': 1, 'rate': 1.0})
        self.assertEqual(result['saves']['pet']['rate'], 1.0)

    def test_exports_identify_dataset_and_snapshot_without_internal_secret(self):
        self.m.configure(True)
        target = Path(self.tmp.name) / 'export.json'
        self.m.export(target)
        first = json.loads(target.read_text())
        self.now += timedelta(seconds=1)
        self.m.export(target)
        second = json.loads(target.read_text())
        self.assertEqual(first['dataset_id'], second['dataset_id'])
        self.assertLess(first['exported_at'], second['exported_at'])
        self.assertNotIn('salt', second)
        self.assertFalse(self.m.export(self.path))

    def test_cohort_switch_never_mixes_team_care_or_unenrolled_actions(self):
        self.m.configure(True, self.data())
        self.m.event('pet_saved')
        self.m.enroll(cohort='team')
        self.m.observe(self.data())
        self.now += timedelta(hours=13)
        self.m.care_completed('private-task', '2026-11-01 12:00')
        self.m.enroll(cohort='evaluation')
        self.m.observe(self.data())
        self.now += timedelta(days=1)
        self.m.observe(self.data())
        team = self.m.summary(self.now - timedelta(days=3), self.now, cohort='team')
        evaluation = self.m.summary(self.now - timedelta(days=3), self.now, cohort='evaluation')
        self.assertEqual((team['care']['eligible'], team['care']['completed']), (1, 1))
        self.assertEqual((evaluation['care']['eligible'], evaluation['care']['completed']), (1, 0))

    def test_reschedule_duplicate_and_period_cutoff(self):
        self.m.configure(True, self.data())
        self.now += timedelta(hours=6)
        self.m.observe(self.data('2026-11-01 18:00', 'No'))
        self.now += timedelta(hours=13)
        self.m.care_completed('private-task', '2026-11-01 18:00')
        self.m.care_completed('private-task', '2026-11-01 18:00')
        result = self.m.summary(self.now - timedelta(days=1), self.now + timedelta(seconds=1))['care']
        self.assertEqual((result['eligible'], result['completed']), (1, 1))
        prior = self.m.summary(self.now - timedelta(days=1), self.now - timedelta(minutes=30))['care']
        self.assertEqual((prior['eligible'], prior['completed']), (1, 0))

    def test_cancellation_at_due_is_not_before_due(self):
        self.m.configure(True, self.data(repeat='No'))
        self.now += timedelta(hours=12)
        self.m.observe({'routines': []})
        self.now += timedelta(seconds=1)
        self.assertEqual(self.m.summary(self.now - timedelta(days=1), self.now)['care']['eligible'], 1)

    def test_offline_snapshot_does_not_invent_coverage_after_export(self):
        self.m.configure(True, self.data())
        self.now += timedelta(hours=13)
        target = Path(self.tmp.name) / 'snapshot.json'
        self.m.export(target)
        offline = Measurement(Path(self.tmp.name) / 'not-read.json')
        offline.ledger = json.loads(target.read_text())
        self.now += timedelta(days=3)
        self.assertEqual(offline.summary(self.now - timedelta(days=4), self.now)['care']['eligible'], 1)

    def test_long_foreground_idle_is_not_truncated_to_one_day(self):
        with patch('services.measurement.monotonic', return_value=0) as mono:
            self.m.configure(True)
            self.m.screen('Inicio')
            mono.return_value = 200000
            self.now += timedelta(seconds=200000)
            self.m.pause()
        result = self.m.summary(self.now - timedelta(days=3), self.now)
        self.assertEqual(result['idle_seconds'], 199970)

    def test_same_participant_task_is_stable_between_devices_and_changes_between_people(self):
        self.m.configure(True)
        participant = self.m.enroll()
        self.m.observe(self.data())
        first = self.m.ledger['segments'][-1]['task']
        other = Measurement(Path(self.tmp.name) / 'other.json')
        other.configure(True)
        other.enroll(participant)
        other.observe(self.data())
        self.assertEqual(first, other.ledger['segments'][-1]['task'])
        self.m.enroll()
        self.assertTrue(all(s['end'] is not None for s in self.m.ledger['segments']))
        self.m.observe(self.data())
        self.assertNotEqual(first, self.m.ledger['segments'][-1]['task'])

    def test_switch_flushes_previous_participant_time_and_rejects_metadata_mutation(self):
        with patch('services.measurement.monotonic', return_value=0) as mono:
            self.m.configure(True)
            team = self.m.enroll(cohort='team')
            self.m.screen('Inicio')
            mono.return_value = 20
            self.now += timedelta(seconds=20)
            self.m.enroll(cohort='evaluation')
            mono.return_value = 25
            self.now += timedelta(seconds=5)
            self.m.pause()
        bounds = (self.now - timedelta(days=1), self.now + timedelta(seconds=1))
        self.assertEqual(self.m.summary(*bounds, cohort='team')['active_seconds'], 20)
        self.assertEqual(self.m.summary(*bounds, cohort='evaluation')['active_seconds'], 5)
        self.assertFalse(self.m.enroll(team, cohort='evaluation'))
        self.assertFalse(self.m.enroll(team, cohort='team', new_participant=False))

    def test_rejects_backwards_period_even_for_offline_snapshot(self):
        with self.assertRaises(ValueError):
            self.m.summary(self.now, self.now - timedelta(seconds=1))

    def test_disabled_reminders_use_explicit_functional_zone_across_dst(self):
        self.now = datetime(2026, 4, 4, tzinfo=timezone.utc)
        data = self.data('2026-04-04 12:00')
        data['reminder_settings']['enabled'] = False
        data['measurement_timezone'] = 'America/Santiago'
        self.m.configure(True, data)
        self.now = datetime(2026, 4, 5, 17, tzinfo=timezone.utc)
        self.m.care_completed('private-task', '2026-04-05 12:00')
        self.assertEqual(datetime.fromisoformat(self.m.ledger['completions'][-1]['due']).utcoffset(), timedelta(hours=-4))
        result = self.m.summary('2026-04-04T00:00:00Z', '2026-04-06T00:00:00Z')['care']
        self.assertEqual((result['eligible'], result['completed'], result['late']), (2, 1, 1))


if __name__ == '__main__':
    unittest.main()
