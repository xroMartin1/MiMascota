"""Real event-loop checks for pending forms, retries and small UI transitions."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.views import ViewAction, ViewImage
from services.cloud import CloudError
from services.store import empty_data, pet_values
from screens.qr_inbox import QrInboxFeatures


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.temp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.mobile = Mock(configured=False)
        self.s.motion_enabled = lambda: True
        self.output = Path('previews/micro'); self.output.mkdir(parents=True, exist_ok=True)
        self.gate = Event(); self.saved = Mock(); self.submissions = []
        self.s.data = empty_data()
        self.s.data['pets'] = [dict(pet_values(dict(name=name, kind=kind)), id=str(i))
                               for i, (name, kind) in enumerate((('Luna', 'Perro'), ('Milo', 'Gato')))]
        self.s.data['routines'] = [dict(id='care', pet='0', title='Paseo', detail='', due_at='2030-11-16 18:00',
                                       time='2030-11-16 18:00', kind='Cuidado', icon='paw', repeat='No', done=False)]
        self.s.selected_pet = '0'
        assert self.s.save()
        Clock.schedule_once(self.form, .4)

    def form(self, _):
        def failure():
            assert self.gate.wait(4)
            raise CloudError('Sin conexión. Inténtalo otra vez.')
        self.operation = failure
        def submit(values):
            self.submissions.append(values.copy())
            self.s.network(self.operation, self.saved)
        self.modal, self.entries = self.s.form('Guardar perfil', [('name', 'Nombre', 'Luna')], submit, persist=False)
        self.button = next(w for w in self.modal.walk() if isinstance(w, ViewAction) and w.text == 'Continuar')
        self.s._backup_running = True
        self.button.dispatch('on_release')
        Clock.schedule_once(self.pending, .1)

    def pending(self, _):
        assert self.button.disabled and self.button.text == 'Procesando…', 'No pending state on submit'
        assert self.modal in Window.children, 'Pending form was dismissed'
        assert self.entries['name'].text == 'Luna'
        self.button.dispatch('on_release')
        assert len(self.submissions) == 1
        self.s._backup_running = False
        self.gate.set()
        self.failure_checks = 0
        Clock.schedule_once(self.failed, .2)

    def failed(self, _):
        if not self.modal.ids.form_error.text:
            self.failure_checks += 1
            assert self.failure_checks < 20, 'Failed request did not return to form'
            Clock.schedule_once(self.failed, .1)
            return
        assert not self.s.busy
        assert self.modal in Window.children and not self.button.disabled
        assert self.entries['name'].text == 'Luna'
        assert self.modal.ids.form_error.text == 'Sin conexión. Inténtalo otra vez.'
        self.saved.assert_not_called()
        self.modal.export_to_png(str(self.output/'error-con-datos.png'))
        self.operation = lambda: 'ok'
        self.retry_checks = 0
        self.button.dispatch('on_release')
        Clock.schedule_once(self.retried, .3)

    def retried(self, _):
        if self.s.busy or self.modal in Window.children:
            self.retry_checks += 1
            assert self.retry_checks < 15, 'Successful form did not close'
            Clock.schedule_once(self.retried, .1)
            return
        self.saved.assert_called_once_with('ok')
        assert self.submissions == [{'name': 'Luna'}, {'name': 'Luna'}]
        assert self.modal not in Window.children
        self.local_retry()

    def local_retry(self):
        original_form = self.s.form
        def capture(*args, **kwargs):
            self.local_modal, self.local_entries = original_form(*args, **kwargs)
            return self.local_modal, self.local_entries
        with patch.object(self.s, 'form', side_effect=capture):
            self.s.register_pet(pet=self.s.data['pets'][0])
        self.local_entries['name'].text = 'Luna nueva'
        with patch.object(self.s.store, 'save', side_effect=OSError('disk full')), patch.object(self.s, 'message'):
            self.local_modal.ids.form_submit.dispatch('on_release')
        assert self.local_modal in Window.children
        assert self.local_entries['name'].text == 'Luna nueva'
        assert self.s.data['pets'][0]['name'] == 'Luna'
        self.local_modal.ids.form_submit.dispatch('on_release')
        assert self.s.data['pets'][0]['name'] == 'Luna nueva'
        with patch.object(self.s, 'form', side_effect=capture):
            self.s.qr_contact_form(self.s.data['pets'][0])
        self.local_entries['share_phone'].text = 'Sí, incluir contacto'
        self.local_entries['name'].text = 'Martín'
        self.local_entries['phone'].text = '+56912345678'
        with patch.object(self.s.store, 'save', side_effect=OSError('disk full')), patch.object(self.s, 'message'):
            self.local_modal.ids.form_submit.dispatch('on_release')
        assert self.local_modal in Window.children
        self.local_modal.ids.form_submit.dispatch('on_release')
        assert self.s.data['pets'][0]['qr_contact']['name'] == 'Martín'
        self.reply_retry()
        Clock.schedule_once(self.open_preview, .3)

    def reply_retry(self):
        captured = {}
        def capture(title, fields, submit, **kwargs):
            captured['submit'] = submit
        with patch.object(self.s, 'form', side_effect=capture), patch.object(self.s, 'qr_owner', return_value='owner'):
            QrInboxFeatures.reply_qr_message(self.s, 'thread')
            with patch.object(self.s, 'network'), patch('screens.qr_inbox.uuid4', side_effect=['first', 'second']) as ids:
                captured['submit']({'detail': 'Hola'})
                captured['submit']({'detail': 'Hola'})
                assert self.s._qr_reply_draft['request'] == 'first'
                captured['submit']({'detail': 'Otro mensaje'})
                assert self.s._qr_reply_draft['request'] == 'second'
                assert ids.call_count == 2

    def open_preview(self, _):
        self.s.preview_tag(False)
        Clock.schedule_once(self.preview, .3)

    def preview(self, _):
        self.modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        image = next(w for w in self.modal.walk() if isinstance(w, ViewImage))
        assert Path(image.source).name == 'chapa-web-3d.png'
        assert image.width > 250 and image.height > 250
        next(w for w in self.modal.walk() if isinstance(w, ViewAction) and w.text == 'Ver reverso').dispatch('on_release')
        assert Path(image.source).name == 'chapa-web-3d-reverso.png'
        Clock.schedule_once(self.care, .3)

    def care(self, _):
        self.modal.export_to_png(str(self.output/'chapa-ampliada.png'))
        self.modal.dismiss(animation=False)
        self.s.show('Rutina')
        self.s.toggle_routine('care')
        button = next(w for w in self.s.content.walk() if isinstance(w, ViewAction) and w.text == 'Reabrir')
        assert button.icon == 'check-circle' and button.visual_scale < 1
        with patch.object(self.s.store, 'save', side_effect=OSError('disk full')), patch.object(
                self.s, 'saved_feedback') as feedback, patch.object(self.s, 'message'):
            self.s.toggle_routine('care')
            feedback.assert_not_called()
        self.s.select_pet('1')
        assert self.s.content.opacity < 1 and self.s.selected_pet == '1'
        self.settle_checks = 0
        Clock.schedule_once(self.settled, .3)

    def settled(self, _):
        if self.s.content.opacity < 1:
            self.settle_checks += 1
            assert self.settle_checks < 15, 'Pet transition did not finish'
            Clock.schedule_once(self.settled, .1)
            return
        assert self.s.content.opacity == 1
        self.s.motion_enabled = lambda: False
        self.s.select_pet('0')
        assert self.s.content.opacity == 1
        self.stop(); self.temp.cleanup()
        print('PASS: pending form, preserved error/retry, tag enlargement/sides, care success/failure and pet transition/reduced motion')


if __name__ == '__main__': Check().run()
