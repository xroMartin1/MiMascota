"""Offline smoke test of consent, evaluation UI and persistence boundaries."""
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import MiMascotaApp
from kivy.clock import Clock
from kivy.core.window import Window
from screens.views import ViewAction, ViewText
from services.mobile import MobileServices
from services.store import LocalStore


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        self.out = Path('previews/mjv-ui')
        self.out.mkdir(parents=True, exist_ok=True)
        self.cloud = Mock(user=None, configured=False, config={}, site_url='https://mi-mascota-web.vercel.app')
        with patch('screens.home.DATA_FILE', Path(self.temp.name) / 'initial.json'), patch('screens.home.Supabase', return_value=self.cloud), patch('screens.home.MobileServices', return_value=MobileServices({})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.steps = self.scenarios()
        self.capture_item = None
        Clock.schedule_once(self.advance, .4)

    def advance(self, _):
        if self.capture_item:
            name, widget, footer = self.capture_item
            assert widget.height <= Window.height, name
            for item in widget.walk():
                if isinstance(item, ViewText) and item.wrap:
                    assert item.height + 1 >= item.texture_size[1], (name, item.text)
            if footer:
                assert widget.y <= footer.y and footer.top <= widget.top, name + ': footer clipped'
            widget.export_to_png(str(self.out / (name + '.png')))
        try:
            self.capture_item = next(self.steps)
            Clock.schedule_once(self.advance, .4)
        except StopIteration:
            self.stop()
            self.temp.cleanup()
            print('PASS: offline MJV UI 390/320, consent, enrollment, validation/storage failure, persisted pet, original care due, Premium screen dedupe/close, private JSON export and device-wide revocation')

    def dismiss(self):
        for widget in list(Window.children):
            if hasattr(widget, 'dismiss'):
                widget.dismiss(animation=False)

    def form(self, action):
        captured = []
        original = self.s.form
        def build(*args, **kwargs):
            result = original(*args, **kwargs)
            captured.append(result)
            return result
        with patch.object(self.s, 'form', side_effect=build):
            action()
        assert len(captured) == 1
        return captured[0]

    def click(self, widget, text):
        target = next(item for item in widget.walk() if isinstance(item, ViewAction) and item.text == text)
        target.dispatch('on_release')

    def events(self, name):
        return [r for r in self.s.measurement.ledger.get('events', []) if r['name'] == name]

    def scenarios(self):
        s = self.s
        for width in (390, 320):
            self.dismiss()
            Window.size = (width, 844 if width == 390 else 640)
            folder = Path(self.temp.name) / str(width)
            s.guest_file = s.data_file = folder / 'guest.json'
            s.store = LocalStore(s.data_file)
            s.data = deepcopy(s.store.data)
            s.cloud.user = None
            s.start_measurement()
            s.account()
            assert not s.statistics_enabled() and not s.measurement.enabled
            assert not s.measurement.path.exists()
            assert any(getattr(w, 'text', '') == 'Privacidad y estadísticas' for w in s.content.walk())
            yield f'guest-account-{width}', s, None

            modal, fields = self.form(s.statistics_preferences)
            assert fields['analytics'].text == 'No'
            yield f'consent-default-{width}', modal, modal.ids.form_submit
            fields['analytics'].text = 'Sí'
            modal.ids.form_submit.dispatch('on_release')
            assert s.statistics_enabled() and s.measurement.enabled and s.measurement.path.exists()
            s.cloud.user = {'id': 'fixture-owner', 'email': 'private-account@example.invalid'}
            s.account()
            assert any(getattr(w, 'context', {}).get('title') == 'Privacidad y estadísticas' for w in s.content.walk())
            yield f'account-privacy-{width}', s, None
            s.cloud.user = None

            modal, fields = self.form(s.enroll_measurement)
            fields['code'].text = '1234567890abcdef1234567890abcdef'
            yield f'enrollment-{width}', modal, modal.ids.form_submit
            modal.ids.form_submit.dispatch('on_release')
            assert s.measurement.ledger['participant'] == '1234567890abcdef1234567890abcdef'
            assert s.measurement.ledger['participants'][0]['new'] is True
            self.dismiss()

            modal, fields = self.form(s.register_pet)
            fields['kind'].text = 'Perro'
            modal.ids.form_submit.dispatch('on_release')
            assert modal.ids.form_error.text and not s.data['pets']
            assert self.events('save_result')[-1]['params'] == {'operation': 'pet', 'result': 'validation'}
            assert not self.events('pet_saved')
            yield f'pet-validation-{width}', modal, modal.ids.form_submit
            fields['name'].text = 'MascotaSecreta'
            with patch.object(s.store, 'save', side_effect=OSError('fixture disk failure')):
                modal.ids.form_submit.dispatch('on_release')
            assert modal.ids.form_error.text and not s.data['pets']
            assert self.events('save_result')[-1]['params']['result'] == 'failed'
            assert not self.events('pet_saved')
            self.dismiss()
            modal, fields = self.form(s.register_pet)
            fields['kind'].text = 'Perro'
            fields['name'].text = 'MascotaSecreta'
            modal.ids.form_submit.dispatch('on_release')
            assert len(s.data['pets']) == 1 and len(self.events('pet_saved')) == 1
            assert json.loads(s.data_file.read_text(encoding='utf-8'))['pets'][0]['name'] == 'MascotaSecreta'
            assert self.events('save_result')[-1]['params']['result'] == 'success'
            self.dismiss()

            s.show('Rutina')
            modal, fields = self.form(s.add_routine)
            due = (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M')
            fields['title'].text = 'CuidadoSecreto'
            fields['detail'].text = 'DiagnosticoSecreto'
            fields['due_at'].text = due
            fields['repeat'].text = 'Diaria'
            modal.ids.form_submit.dispatch('on_release')
            task = s.data['routines'][0]
            assert task['due_at'] == due
            self.dismiss()
            toggle = next(w for w in s.content.walk() if isinstance(w, ViewAction) and getattr(w, 'context', {}).get('task_id') == task['id'])
            toggle.dispatch('on_release')
            assert self.events('care_complete')[-1]['params'] == {'result': 'completed'}
            completed = s.measurement.ledger['completions'][-1]
            assert datetime.fromisoformat(completed['due']).strftime('%Y-%m-%d %H:%M') == due
            assert completed['task'] != task['id'] and task['due_at'] != due
            assert 'MascotaSecreta' not in json.dumps(s.measurement.ledger)
            yield f'care-completed-{width}', s, None

            s.cloud.user = {'id': 'fixture-owner'}
            s.render_subscription(s.data['pets'][0], {'state': 'none'})
            assert s.measurement.current == 'Premium'
            assert sum(r['params']['screen'] == 'Premium' for r in self.events('screen_view')) == 1
            yield f'premium-{width}', s._billing_modal, next(w for w in s._billing_modal.ids.card.children if isinstance(w, ViewAction))
            s.render_subscription(s.data['pets'][0], {'state': 'none'})
            yield f'premium-refresh-{width}', s._billing_modal, next(w for w in s._billing_modal.ids.card.children if isinstance(w, ViewAction))
            assert s.measurement.current == 'Premium'
            assert sum(r['params']['screen'] == 'Premium' for r in self.events('screen_view')) == 1
            s._billing_modal.dismiss(animation=False)
            yield f'premium-return-{width}', s, None
            assert s.measurement.current == s.active == 'Rutina'

            with patch('services.health_report.share_health_report') as share:
                s.export_measurement()
                notice = next(w for w in Window.children if getattr(w, 'context', {}).get('text') == 'Compartir estadísticas')
                yield f'export-confirm-{width}', notice, None
                share.assert_not_called()
                self.click(notice, 'Confirmar')
                share.assert_called_once()
                path = Path(share.call_args.args[0])
                assert share.call_args.kwargs['mime'] == 'application/json'
                payload = json.loads(path.read_text(encoding='utf-8'))
                assert payload['version'] == 1 and payload['events'] and payload['completions']
                assert 'salt' not in payload
                for secret in ('MascotaSecreta', 'CuidadoSecreto', 'DiagnosticoSecreto', 'private-account@example.invalid', 'fixture-owner'):
                    assert secret not in json.dumps(payload), secret
                path.unlink()
            self.dismiss()
            other = s.measurement.path.parent / 'other-account.json'
            other.write_text('{"events": []}', encoding='utf-8')
            care_before = s.data_file.read_bytes()
            modal, fields = self.form(s.statistics_preferences)
            fields['analytics'].text = 'No'
            yield f'revoke-{width}', modal, modal.ids.form_submit
            modal.ids.form_submit.dispatch('on_release')
            assert not s.statistics_enabled() and not s.measurement.enabled
            assert not list(s.measurement.path.parent.glob('*.json'))
            assert s.data_file.read_bytes() == care_before and s.data['routines']
            self.dismiss()


if __name__ == '__main__':
    with patch('requests.request', side_effect=AssertionError('No network in offline UI check')), patch('webbrowser.open', side_effect=AssertionError('No browser in offline UI check')):
        Check().run()
