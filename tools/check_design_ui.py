"""Visual regression checks with synthetic data and no account or cloud access."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from main import MiMascotaApp
from screens.views import ViewAction, ViewText, view
from services.store import empty_data, pet_values
from tests.test_qr_inbox import conversation


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.temp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.mobile = Mock(configured=False)
        self.s.network = lambda *args, **kwargs: None
        self.output = Path('previews/design-after')
        self.output.mkdir(parents=True, exist_ok=True)
        self.failures = []
        if sys.platform == 'win32':
            from screens.views import motion_enabled
            with patch('ctypes.windll.user32.SystemParametersInfoW', side_effect=lambda flag, size, value, update:
                       (setattr(value._obj, 'value', 0), 1)[1]):
                self.check(not motion_enabled(), 'Windows reduced motion ignored')
        self.s.data = empty_data()
        for i, (name, kind) in enumerate((('Luna', 'Perro'), ('Milo', 'Gato'))):
            pet = pet_values(dict(name=name, kind=kind, breed='Golden retriever' if i == 0 else 'Europeo', age='3 años'))
            self.s.data['pets'].append(dict(pet, id=str(i)))
        self.s.selected_pet = '0'
        self.s.data['routines'] = [dict(id='care', pet='0', title='Paseo de la tarde', detail='Un paseo tranquilo.',
            due_at='2030-11-16 18:30', time='2030-11-16 18:30', kind='Cuidado', icon='walk', repeat='No', done=False)]
        self.states = iter((width, page) for width in (390, 320) for page in ('Inicio', 'Mascotas', 'Rutina', 'Salud', 'Chapa', 'Cuenta'))
        Clock.schedule_once(self.next_page, .4)

    def check(self, condition, message):
        if not condition:
            self.failures.append(message)

    def next_page(self, _):
        item = next(self.states, None)
        if item is None:
            self.date_form(None)
            return
        self.width, self.page = item
        Window.size = (self.width, 844 if self.width == 390 else 640)
        self.s.show(self.page)
        Clock.schedule_once(self.capture, .4)

    def capture(self, _):
        self.root.export_to_png(str(self.output/f'{self.page}-{self.width}.png'))
        for w in self.s.content.walk():
            if isinstance(w, ViewText) and w.wrap and w.width > 0:
                self.check(w.height + 1 >= w.texture_size[1], f'Clipped text: {self.page}: {w.text}')
            if isinstance(w, ViewAction) and w.text and not w.vertical:
                label = next(c for c in w.children if isinstance(c, ViewText) and c.text == w.text)
                self.check(abs(label.center_y - w.center_y) < dp(1), f'Button text off center: {w.text}')
                self.check(w.bg != '#F28B74', f'Normal action uses error color: {w.text}')
        self.check(sum(bool(b.context.get('selected')) for b in self.s.nav.children) <= 1, 'Multiple selected tabs')
        if self.page == 'Salud':
            self.check(not any(w.text.startswith('Peso: Sin registrar') for w in self.s.content.walk()
                               if isinstance(w, ViewText)), 'Health summary presented a missing weight')
        for button in self.s.nav.children:
            label = next(w for w in button.children if isinstance(w, ViewText) and w.text == button.text)
            self.check(not label.is_shortened, f'Tab label clipped at {self.width}px: {button.text}')
        Clock.schedule_once(self.next_page, .01)

    def date_form(self, _):
        self.modal, entries = self.s.form('Fecha y hora', [('date', 'Fecha y hora', '2030-11-16 18:30')], lambda _: None)
        self.date_field = entries['date']
        Clock.schedule_once(self.check_date, .4)

    def check_date(self, _):
        self.modal.export_to_png(str(self.output/'fecha-320.png'))
        for button in (self.date_field.date_button, self.date_field.time_button):
            label = next(w for w in button.children if isinstance(w, ViewText) and w.text == button.text)
            self.check(not label.is_shortened, f'Date/time clipped at 320px: {button.text}')
        self.check(self.date_field.text == '2030-11-16 18:30', 'Date storage format changed')
        Window.size = (320, 560)
        Clock.schedule_once(self.check_resized_form, .4)

    def check_resized_form(self, _):
        self.check(self.modal.height >= dp(240), 'Height-only resize collapsed compact form')
        self.modal.dismiss(animation=False)
        task = dict(self.s.data['routines'][0], title='Control veterinario y revisión después del tratamiento',
                    detail='Detalles del cuidado y pauta indicada por el veterinario. ' * 20)
        self.s.task_detail(task)
        self.modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        Clock.schedule_once(self.check_task, .4)

    def check_task(self, _):
        card = self.modal.ids.card
        self.modal.export_to_png(str(self.output/'detalle-largo-320.png'))
        self.check(all(w.y >= card.y and w.top <= card.top for w in card.children), 'Long task overflowed its dialog')
        self.modal.dismiss(animation=False)
        Window.size = (320, 640)
        self.s.cloud.user = {'id': 'fixture'}
        self.s._qr_owner = 'fixture'
        self.s.qr_conversation_panel(conversation())
        Clock.schedule_once(self.check_chat, .5)

    def check_chat(self, _):
        self.root.export_to_png(str(self.output/'conversacion-320.png'))
        self.check(self.s.content.top + self.s.scroll.g_translate.y >= self.s.scroll.top - dp(2),
                   'Short conversation is bottom aligned')
        result = conversation()
        result['messages'] *= 12
        self.s.qr_conversation_panel(result)
        Clock.schedule_once(self.check_long_chat, .4)

    def check_long_chat(self, _):
        self.check(self.s.scroll.scroll_y == 0, 'Long conversation did not scroll to reply')
        self.s.qr_conversation_panel(conversation())
        self.s.show('Inicio')
        Clock.schedule_once(self.check_chat_timer, .15)

    def check_chat_timer(self, _):
        self.check(self.s.scroll.scroll_y == 1, 'Conversation callback moved another page')
        self.original_motion = self.s.motion_enabled
        self.s.motion_enabled = lambda: False
        button = view('HomeRegisterPet', callback=lambda *_: None)
        self.s.content.add_widget(button)
        button.state = 'down'
        button.state = 'normal'
        self.check(button.opacity == 1, 'Reduced motion left a faded button')
        self.check(getattr(button, 'press_amount', None) == 0, 'Press feedback did not settle without motion')
        # Failed storage must not show a successful completion or keep its mutation.
        with patch.object(self.s.store, 'save', side_effect=OSError('disk full')), patch.object(
                self.s, 'message') as error, patch.object(self.s, 'saved_feedback') as success:
            self.s.toggle_routine('care')
            self.check(error.called and not success.called, 'Failed save reported successful care completion')
        self.s.message('Guardado', 'Cambios guardados.')
        self.modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        Clock.schedule_once(self.check_dialog, .4)

    def check_dialog(self, _):
        self.modal.export_to_png(str(self.output/'mensaje-320.png'))
        self.check(self.modal.height < dp(240), 'Short message dialog wastes space')
        self.check(self.modal._anim_duration == 0 and self.modal.ids.card.visual_scale == 1,
                   'Reduced motion did not settle dialog immediately')
        self.modal.dismiss(animation=False)
        self.s.motion_enabled = self.original_motion
        button = view('HomeRegisterPet', callback=lambda *_: None)
        self.s.content.add_widget(button)
        for state in ('down', 'normal', 'down', 'normal'):
            button.state = state
        self.button = button
        self.s.motion_enabled = lambda: True
        self.s.message('Guardado', 'Cambios guardados.')
        self.modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        Clock.schedule_once(self.interrupt_dialog, .04)

    def interrupt_dialog(self, _):
        scale = self.modal.ids.card.visual_scale
        self.modal.dismiss()
        self.check(abs(self.modal.ids.card.visual_scale - scale) < .00001, 'Interrupted dialog scale jumped')
        self.s.motion_enabled = self.original_motion
        Clock.schedule_once(self.finish, .3)

    def finish(self, _):
        self.check(getattr(self.button, 'press_amount', None) == 0, 'Interrupted press did not settle')
        self.temp.cleanup()
        self.stop()
        assert not self.failures, '\n'.join(self.failures)
        print('PASS: 12 pages, 320px date/time, short conversation, navigation, compact dialogs and interrupted/reduced motion')


if __name__ == '__main__':
    Check().run()
