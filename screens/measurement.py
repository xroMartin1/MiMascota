"""Consentimiento y adaptación de la medición; nunca interrumpe el cuidado."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4


class MeasurementFeatures:
    def measurement_call(self, method, *args, **kwargs):
        try:
            return getattr(self.measurement, method)(*args, **kwargs)
        except Exception:
            return None  # La medición opcional no condiciona el guardado funcional.

    def statistics_enabled(self):
        if hasattr(self, '_statistics_override'):
            return self._statistics_override
        try:
            choice_path = self.guest_file.parent / 'usage-choice.json'
            choice = json.loads(choice_path.read_text(encoding='utf-8')) if choice_path.exists() else {}
            if choice.get('enabled') is False:
                return False
            if self.mobile.configured:
                return self.mobile.preferences()['analytics'] is True
            return choice.get('enabled') is True
        except (OSError, ValueError, TypeError, AttributeError):
            return False

    def measurement_data(self):
        try:
            choice = json.loads((self.guest_file.parent / 'usage-choice.json').read_text(encoding='utf-8'))
            zone = choice.get('timezone')
        except (OSError, ValueError, TypeError, AttributeError):
            zone = None
        if not zone:
            from services.reminders import suggested_zone
            zone = suggested_zone()
        return {'routines': self.data.get('routines', []),
                'reminder_settings': self.data.get('reminder_settings', {}), 'measurement_timezone': zone}

    def start_measurement(self):
        self.measurement = None
        try:
            from services.measurement import Measurement
            key = hashlib.sha256(str(self.data_file.resolve()).encode()).hexdigest()[:24]
            self.measurement = Measurement(self.guest_file.parent / 'usage' / (key + '.json'),
                                           sender=lambda name, params: self.mobile.event(name, params))
            self.measurement_call('configure', self.statistics_enabled(), self.measurement_data())
        except Exception:
            pass

    def track_event(self, name, **params):
        self.measurement_call('event', name, **params)

    def observe_measurement(self):
        try:
            self.measurement_call('observe', self.measurement_data())
        except Exception:
            pass

    def measurement_screen(self, name):
        name = {'Conversación': 'Avisos', 'Compartidos': 'Cuenta',
                'Cuidado compartido': 'Cuenta'}.get(name, name)
        self.measurement_call('screen', name)

    def record_care_completion(self, task_id, due_at, undo=False):
        self.measurement_call('care_completed', task_id, due_at, undo=undo)

    def measurement_touch(self, *_):
        self.measurement_call('touch')
        return False

    def pause_measurement(self):
        self.measurement_call('pause')

    def resume_measurement(self):
        self.measurement_call('resume')

    def set_statistics(self, enabled, timezone=None):
        if not enabled:
            self._statistics_override = False
            self.measurement_call('configure', False, self.data)
        choice = self.guest_file.parent / 'usage-choice.json'
        failed = False
        try:
            if self.mobile.configured:
                prefs = self.mobile.preferences()
                if prefs['analytics'] != enabled:
                    self.mobile.configure(prefs['notifications'], enabled)
        except Exception:
            failed = True
        try:
            if timezone is None:
                timezone = self.measurement_data()['measurement_timezone']
            from zoneinfo import ZoneInfo
            ZoneInfo(timezone)
            choice.parent.mkdir(parents=True, exist_ok=True)
            temp = choice.with_suffix('.tmp')
            temp.write_text(json.dumps({'enabled': bool(enabled), 'timezone': timezone}), encoding='utf-8')
            temp.replace(choice)
        except (OSError, ValueError, KeyError):
            failed = True
        if not enabled:
            # La revocación también alcanza registros de otras cuentas de este dispositivo.
            for path in (self.guest_file.parent / 'usage').glob('*'):
                if path.suffix in ('.json', '.tmp'):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        failed = True
        if failed:
            detail = 'La medición local está desactivada.' if not enabled else 'No se pudo activar la medición.'
            raise ValueError(detail + ' No pudimos guardar todos los cambios. Inténtalo otra vez.')
        self._statistics_override = bool(enabled)
        if enabled:
            self.measurement_call('configure', True, self.measurement_data())
            self.measurement_screen(self.active)

    def statistics_preferences(self, *_):
        from screens.views import view
        from services.reminders import ZONES, ZONE_LABELS
        enabled = self.statistics_enabled()
        selected_zone = self.measurement_data()['measurement_timezone']
        zones = dict((ZONE_LABELS.get(z, z).replace(' · ', ' - '), z) for z in dict.fromkeys((selected_zone,) + ZONES))
        current_zone = next(label for label, zone in zones.items() if zone == selected_zone)
        def submit(values):
            self.set_statistics(values['analytics'] == 'Sí', zones[values['timezone']])
        modal, _ = self.form('Estadísticas de uso', [
            ('analytics', '¿Compartir estadísticas de uso?', 'Sí' if enabled else 'No'),
            ('timezone', 'Zona horaria de tus cuidados', current_zone)],
            submit, choices={'analytics': ('No', 'Sí'), 'timezone': tuple(zones)}, persist=False,
            description='Es opcional. Nos ayuda a mejorar la app. No compartimos nombres, contactos ni el historial de tus mascotas. Puedes desactivarlo cuando quieras.',
            submit_text='Guardar preferencia')
        if enabled:
            def action(callback):
                def run(*_):
                    modal.dismiss()
                    callback()
                return run
            modal.ids.form_inputs.add_widget(view('AccountAction', text='Participar en una prueba de uso',
                                                  callback=action(self.enroll_measurement)))
            modal.ids.form_inputs.add_widget(view('AccountAction', text='Compartir mis estadísticas',
                                                  callback=action(self.export_measurement)))

    def enroll_measurement(self):
        import re
        if not self.statistics_enabled():
            self.statistics_preferences()
            return
        def submit(values):
            code = values['code'].strip()
            if code and not re.fullmatch(r'[a-fA-F0-9]{32}', code):
                raise ValueError('Usa el código de prueba de 32 caracteres o deja el campo vacío.')
            cohort = 'evaluation' if values['group'] == 'Participante' else 'team'
            result = self.measurement_call('enroll', participant=code.lower() or None, cohort=cohort,
                                           new_participant=not self.data['pets'])
            if not result:
                raise ValueError('No pudimos comenzar la prueba. Inténtalo otra vez.')
            self.observe_measurement()
            self.message('Prueba iniciada', 'Tu código es ' + str(result) + '. Puedes usarlo en otro dispositivo durante esta misma prueba.')
        self.form('Prueba de uso', [('code', 'Código de prueba (opcional)', ''),
                                   ('group', 'Participación', 'Participante')], submit,
                  choices={'group': ('Participante', 'Equipo')}, persist=False,
                  description='Participa solo si recibiste una invitación. Usa el código que te entregaron o déjalo vacío para generar uno. No escribas tu nombre ni tu correo.',
                  submit_text='Comenzar prueba')

    def export_measurement(self):
        if not self.statistics_enabled():
            self.statistics_preferences()
            return
        self.confirm('Compartir estadísticas',
                     'Se compartirá un archivo con el uso de la app y tu código de prueba, sin nombres, contactos ni historial de salud. Elige con quién compartirlo.',
                     self.prepare_measurement_export)

    def prepare_measurement_export(self):
        from services.health_report import share_health_report
        from kivy.logger import Logger
        from kivy.utils import platform
        try:
            if platform == 'android':
                from jnius import autoclass
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                folder = Path(str(activity.getCacheDir().getAbsolutePath()))
            else:
                from tempfile import gettempdir
                folder = Path(gettempdir()) / 'mimascota'
            folder = folder / 'usage-exports'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / ('uso-' + uuid4().hex + '.json')
            if not self.measurement_call('export', path):
                raise OSError('measurement export unavailable')
        except Exception:
            Logger.exception('Measurement: could not prepare statistics export')
            self.message('No se pudieron preparar las estadísticas', 'Inténtalo otra vez. Revisa el espacio disponible.')
            return
        try:
            share_health_report(path, mime='application/json', title='Estadísticas de uso')
        except Exception:
            Logger.exception('Measurement: could not share statistics export')
            self.message('No se pudo compartir', 'El archivo se preparó, pero no pudimos abrir el menú para compartir. Inténtalo otra vez. Revisa que tengas una app para compartir archivos.')
