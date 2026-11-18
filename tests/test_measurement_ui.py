import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from screens.measurement import MeasurementFeatures


class MeasurementIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.screen = MeasurementFeatures()
        self.screen.measurement = Mock()
        self.screen.data = {'pets': [], 'routines': []}

    def test_observes_only_supplied_functional_snapshot(self):
        snapshot = {'routines': []}
        with patch.object(self.screen, 'measurement_data', return_value=snapshot):
            self.screen.observe_measurement()
        self.screen.measurement.observe.assert_called_once_with(snapshot)

    def test_telemetry_failure_does_not_escape_into_care_flow(self):
        self.screen.measurement.event.side_effect = OSError('disk full')
        self.screen.measurement.observe.side_effect = ValueError('invalid measurement')
        self.screen.measurement.screen.side_effect = RuntimeError('SDK unavailable')
        self.screen.track_event('save_result', operation='care', result='success')
        self.screen.observe_measurement()
        self.screen.measurement_screen('Rutina')

    def test_completed_occurrence_keeps_original_due_and_undo(self):
        self.screen.record_care_completion('local-id', '2026-11-17 12:00', True)
        self.screen.measurement.care_completed.assert_called_once_with(
            'local-id', '2026-11-17 12:00', undo=True)

    def test_lifecycle_flushes_and_never_blocks_pause(self):
        self.screen.pause_measurement()
        self.screen.measurement.pause.assert_called_once_with()
        self.screen.measurement.resume.side_effect = OSError()
        self.screen.resume_measurement()

    def test_revocation_stops_measurement_even_if_choice_cannot_be_written(self):
        with TemporaryDirectory() as folder:
            self.screen.guest_file = Path(folder) / 'guest.json'
            self.screen.mobile = Mock(configured=False)
            (Path(folder) / 'usage-choice.json').write_text(json.dumps({'enabled': True}))
            with patch('pathlib.Path.write_text', side_effect=OSError('disk unavailable')):
                with self.assertRaises(ValueError):
                    self.screen.set_statistics(False)
            self.screen.measurement.configure.assert_called_once_with(False, self.screen.data)
            self.assertFalse(self.screen.statistics_enabled())

    def test_revocation_removes_other_account_temporary_files(self):
        with TemporaryDirectory() as folder:
            self.screen.guest_file = Path(folder) / 'guest.json'
            self.screen.mobile = Mock(configured=False)
            usage = Path(folder) / 'usage'
            usage.mkdir()
            for name in ('other.json', 'other.tmp'):
                (usage / name).write_text('{}')
            self.screen.set_statistics(False)
            self.assertEqual(list(usage.iterdir()), [])

    def test_export_failure_reports_preparation_without_trying_to_share(self):
        self.screen.message = Mock()
        self.screen.measurement.export.return_value = None
        with TemporaryDirectory() as folder, patch('tempfile.gettempdir', return_value=folder), \
                patch('kivy.utils.platform', 'win'), patch('kivy.logger.Logger.exception'), \
                patch('services.health_report.share_health_report') as share:
            self.screen.prepare_measurement_export()
        share.assert_not_called()
        self.assertEqual(self.screen.message.call_args.args[0], 'No se pudieron preparar las estadísticas')

    def test_share_failure_keeps_prepared_statistics_and_reports_sharing(self):
        self.screen.message = Mock()
        def export(path):
            path.write_text('{}', encoding='utf-8')
            return path
        self.screen.measurement.export.side_effect = export
        with TemporaryDirectory() as folder, patch('tempfile.gettempdir', return_value=folder), \
                patch('kivy.utils.platform', 'win'), patch('kivy.logger.Logger.exception'), \
                patch('services.health_report.share_health_report', side_effect=RuntimeError('JNI failure')):
            self.screen.prepare_measurement_export()
            self.assertEqual(len(list(Path(folder).rglob('uso-*.json'))), 1)
        self.assertEqual(self.screen.message.call_args.args[0], 'No se pudo compartir')


if __name__ == '__main__':
    unittest.main()
