import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.report_measurement import build_report, write_report


class MeasurementReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.participant = 'a' * 32
        self.base = {'version': 1, 'dataset_id': 'b' * 32, 'exported_at': '2026-11-17T13:00:00Z',
                     'coverage_start': '2026-11-17T10:00:00Z', 'segments': [], 'completions': [],
                     'participants': [{'at': '2026-11-17T10:00:00Z', 'participant': self.participant,
                                       'cohort': 'evaluation', 'new': True}],
                     'events': [{'at': '2026-11-17T11:00:00Z', 'name': 'pet_saved', 'params': {},
                                 'participant': self.participant, 'cohort': 'evaluation'}]}

    def save(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_duplicate_exports_use_newest_snapshot_and_deduplicate_participants(self):
        older = self.save('old.json', self.base)
        self.base['exported_at'] = '2026-11-17T14:00:00Z'
        newer = self.save('new.json', self.base)
        result = build_report([older, newer], '2026-11-17T09:00:00Z', '2026-11-17T15:00:00Z')
        self.assertEqual(result['datasets'], 1)
        self.assertEqual(result['activation']['activated'], 1)
        self.assertEqual(result['activation']['rate'], 1)
        self.assertIsNone(result['care']['rate'])
        write_report(result, self.root / 'out')
        html = (self.root / 'out/report.html').read_text(encoding='utf-8')
        self.assertIn('Sin datos', html)
        self.assertIn('2026-11-17', html)
        self.assertNotIn(self.participant, html)

    def test_team_is_excluded_and_invalid_event_not_silently_counted(self):
        for key in ('events', 'participants'):
            self.base[key][0]['cohort'] = 'team'
        path = self.save('team.json', self.base)
        result = build_report([path], '2026-11-17T09:00:00Z', '2026-11-17T15:00:00Z')
        self.assertEqual(result['activation']['eligible'], 0)
        self.base['events'][0]['params'] = {'email': 'must-not-be-output@example.invalid'}
        with self.assertRaises(ValueError):
            build_report([self.save('bad.json', self.base)], '2026-11-17T09:00:00Z', '2026-11-17T15:00:00Z')

    def test_payments_count_unique_terminal_orders_and_pending_separately(self):
        orders = {'test_mode': True, 'exported_at': '2026-11-17T14:00:00Z', 'orders': [
            {'order_id': 'order-a', 'state': 'active', 'created_at': '2026-11-17T11:00:00Z'},
            {'order_id': 'order-a', 'state': 'active', 'created_at': '2026-11-17T11:00:00Z'},
            {'order_id': 'order-b', 'state': 'rejected', 'created_at': '2026-11-17T11:00:00Z'},
            {'order_id': 'order-c', 'state': 'pending', 'created_at': '2026-11-17T11:00:00Z'}]}
        selected = self.save('orders.json', {'cohort': 'evaluation', 'order_ids': ['order-a', 'order-b', 'order-c']})
        result = build_report([self.save('data.json', self.base)], '2026-11-17T09:00:00Z',
                              '2026-11-17T15:00:00Z', payments=self.save('pay.json', orders), payment_orders=selected)
        self.assertEqual(result['payments']['rate'], .5)
        self.assertEqual(result['payments']['pending'], 1)

    def test_server_payment_snapshot_must_not_mix_team_into_participants(self):
        orders = self.save('server.json', {'test_mode': True, 'exported_at': '2026-11-17T14:00:00Z', 'orders': [
            {'order_id': 'team-order', 'state': 'active', 'created_at': '2026-11-17T11:00:00Z'},
            {'order_id': 'participant-order', 'state': 'rejected', 'created_at': '2026-11-17T11:00:00Z'}]})
        selected = self.save('selection.json', {'cohort': 'evaluation', 'order_ids': ['participant-order']})
        export = self.save('data.json', self.base)
        result = build_report([export], '2026-11-17T09:00:00Z', '2026-11-17T15:00:00Z',
                              payments=orders, payment_orders=selected)
        self.assertEqual((result['payments']['terminal'], result['payments']['rate']), (1, 0))
        with self.assertRaises(ValueError):
            build_report([export], '2026-11-17T09:00:00Z', '2026-11-17T15:00:00Z', payments=orders)

    def test_same_participant_on_second_device_is_not_a_new_enrollment(self):
        first = self.save('first.json', self.base)
        self.base['dataset_id'] = 'c' * 32
        self.base['participants'][0]['at'] = '2026-11-17T12:00:00Z'
        second = self.save('second.json', self.base)
        result = build_report([first, second], '2026-11-17T11:30:00Z', '2026-11-17T15:00:00Z')
        self.assertEqual(result['activation']['eligible'], 0)

    def test_shared_task_reference_is_not_counted_twice_across_devices(self):
        segment = dict(task='d' * 64, due='2026-11-17T11:00:00Z', repeat='No',
                       start='2026-11-17T10:00:00Z', end=None, zone='UTC',
                       participant=self.participant, cohort='evaluation')
        self.base['segments'] = [segment]
        first = self.save('first.json', self.base)
        self.base['dataset_id'] = 'c' * 32
        self.base['completions'] = [dict(task='d' * 64, due=segment['due'], undo=False,
                                        at='2026-11-17T12:00:00Z', participant=self.participant, cohort='evaluation')]
        result = build_report([first, self.save('second.json', self.base)],
                              '2026-11-17T10:00:00Z', '2026-11-17T15:00:00Z')
        self.assertEqual((result['care']['eligible'], result['care']['completed'], result['care']['rate']), (1, 1, 1))


if __name__ == '__main__':
    unittest.main()
