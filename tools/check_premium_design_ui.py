"""Offline UI checks for the expanded design and breed-dependent forms/portraits."""
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
from kivy.uix.textinput import TextInput
from main import MiMascotaApp
from screens.views import ViewText, ViewAction
from services.pet_profiles import BREEDS
from services.store import empty_data, pet_values


class Check(MiMascotaApp):
    def build(self):
        self.tmp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.tmp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.cloud = Mock(user={'id': 'fixture', 'email': 'fixture@example.invalid', 'user_metadata': {}},
                            configured=False, config={})
        self.s.mobile = Mock(configured=False)
        self.s.data = empty_data()
        for i, (kind, breed) in enumerate((('Perro', 'Pastor alemán'), ('Gato', 'Siamés'))):
            self.s.data['pets'].append(dict(pet_values(dict(name='Luna', kind=kind, breed=breed, age='3', weight='4.5')), id=str(i)))
        self.s.selected_pet = '0'
        self.s.network = Mock()
        self.out = Path('previews/premium-design'); self.out.mkdir(parents=True, exist_ok=True)
        self.states = iter((width, page) for width in (390, 320) for page in ('Inicio', 'Mascotas', 'Cuenta', 'Rutina'))
        Clock.schedule_once(self.next, .3)

    def next(self, _):
        item = next(self.states, None)
        if item is None:
            self.form()
            return
        self.width, self.page = item
        Window.size = (self.width, 844 if self.width == 390 else 640)
        self.s.show(self.page)
        Clock.schedule_once(self.capture, .3)

    def capture(self, _):
        self.root.export_to_png(str(self.out/f'{self.page}-{self.width}.png'))
        assert self.s.subtitle.height == 0 and self.s.subtitle.opacity == 0
        labels = [w.text for w in self.s.content.walk() if isinstance(w, ViewText)]
        assert not any('·' in label for label in labels)
        assert not any(term in label.casefold() for label in labels
                       for term in ('servidor', 'firebase', 'remote config', 'mockup', '.bak', 'data/petcare'))
        if self.page == 'Mascotas':
            assert 'Pastor alemán\n3 años\n4.5 kg' in labels
            portraits = [w for w in self.s.content.walk() if w.__class__.__name__ == 'ViewPetAvatar']
            assert {Path(w.portrait_source).name for w in portraits} == {'pastor-aleman.png', 'siames.png'}
        elif self.page == 'Cuenta':
            button = next(w for w in self.s.content.walk() if isinstance(w, ViewAction) and w.text == 'Ver Premium')
            with patch.object(self.s, 'plan_info') as open_plan:
                button.dispatch('on_release'); open_plan.assert_called_once()
        Clock.schedule_once(self.next, .05)

    def form(self):
        original = self.s.form
        def capture(*args, **kwargs):
            self.modal, self.entries = original(*args, **kwargs)
            return self.modal, self.entries
        with patch.object(self.s, 'form', side_effect=capture):
            self.s.register_pet(pet=self.s.data['pets'][0])
        assert set(BREEDS['Perro']).issubset(self.entries['breed'].values)
        self.entries['kind'].text = 'Gato'
        assert set(BREEDS['Gato']).issubset(self.entries['breed'].values)
        assert 'Pastor alemán' not in self.entries['breed'].values
        self.entries['breed'].text = 'Siamés'
        self.entries['age'].text = '1'
        self.entries['name'].text = 'Nueva Luna'
        Clock.schedule_once(self.inputs, .3)

    def inputs(self, _):
        for entry in self.entries.values():
            if isinstance(entry, TextInput) and not entry.multiline:
                assert abs((entry.height-entry.line_height)/2 - entry.padding[1]) < 1
        self.modal.export_to_png(str(self.out/'editar-mascota-320.png'))
        self.modal.ids.form_submit.dispatch('on_release')
        saved = self.s.data['pets'][0]
        assert (saved['name'], saved['kind'], saved['breed'], saved['age']) == ('Nueva Luna', 'Gato', 'Siamés', '1')
        Clock.schedule_once(self.selector, .3)

    def selector(self, _):
        self.s.plan_info()
        Clock.schedule_once(self.pick, .3)

    def pick(self, _):
        modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        rows = [w for w in modal.walk() if w.__class__.__name__ == 'HealthPetOption']
        assert len(rows) == 2
        target_id = next(p['id'] for p in self.s.data['pets'] if p['name'] == rows[1].context['name'])
        with patch.object(self.s, 'open_subscription') as opened:
            rows[1].dispatch('on_release')
            assert opened.call_args.args[0]['id'] == target_id
            assert opened.call_args.args[0] is next(p for p in self.s.data['pets'] if p['id'] == opened.call_args.args[0]['id'])
        Clock.schedule_once(self.legacy, .3)

    def legacy(self, _):
        original = self.s.form
        def capture(*args, **kwargs):
            self.modal, self.entries = original(*args, **kwargs)
            return self.modal, self.entries
        legacy = self.s.data['pets'][0]
        legacy['kind'], legacy['breed'] = 'gato', 'Otra raza'
        with patch.object(self.s, 'form', side_effect=capture):
            self.s.register_pet(pet=legacy)
        assert self.entries['kind'].text == 'Gato'
        assert self.entries['breed'].text == 'Otra raza'
        assert self.entries['custom_breed'].text == 'Otra raza'
        self.entries['breed'].text = 'Otra raza'
        self.entries['custom_breed'].text = 'Europeo'
        self.entries['name'].text = ''
        Window.size = (320, 480)
        Clock.schedule_once(self.compact, .3)

    def compact(self, _):
        from kivy.graphics import Color
        entry = self.entries['name']
        assert not entry.text and entry.hint_text
        assert abs((entry.height-entry.line_height)/2 - entry.padding[1]) < 1
        colors = [instruction for instruction in entry.canvas.before.children if isinstance(instruction, Color)]
        assert tuple(colors[-1].rgba) == tuple(entry.hint_text_color)
        button = self.modal.ids.form_submit
        assert button.y >= self.modal.y and button.top <= self.modal.top
        self.modal.export_to_png(str(self.out/'placeholder-320-480.png'))
        self.entries['name'].text = 'Nueva Luna'
        self.modal.ids.form_submit.dispatch('on_release')
        legacy = self.s.data['pets'][0]
        assert legacy['breed'] == 'Europeo'
        self.stop(); self.tmp.cleanup()
        print('PASS: 8 page captures, header, portraits, species dropdowns, centered inputs, persisted edit, Premium selection and legacy/custom breeds')


if __name__ == '__main__':
    Check().run()
