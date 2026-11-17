"""Real event-loop checks for portrait previews, tactile cards and dropdowns."""
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
from kivy.base import EventLoop
from kivy.input.motionevent import MotionEvent
from main import MiMascotaApp
from screens.views import ViewAction
from services.store import empty_data, pet_values


class Touch(MotionEvent):
    def __init__(self, x, y):
        super().__init__('portrait-test', 99, {'x': x/(Window.width-1), 'y': y/(Window.height-1)},
                         is_touch=True, type_id='touch')
        self.profile = ['pos']

    def depack(self, args):
        self.sx, self.sy = args['x'], args['y']
        super().depack(args)

    def down(self):
        EventLoop.post_dispatch_input('begin', self)

    def drag(self, x, y):
        self.move({'x': x/(Window.width-1), 'y': y/(Window.height-1)})
        EventLoop.post_dispatch_input('update', self)

    def up(self):
        EventLoop.post_dispatch_input('end', self)


class Check(MiMascotaApp):
    def build(self):
        self.tmp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.tmp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.motion_enabled = lambda: True
        self.s.mobile = Mock(configured=False)
        self.s.data = empty_data()
        for i, (kind, breed) in enumerate((('Gato', 'Siamés'), ('Perro', 'Golden retriever'), ('Reptil', 'Iguana'))):
            self.s.data['pets'].append(dict(pet_values(dict(name='Luna '+str(i), kind=kind, breed=breed, age='3')), id=str(i)))
        self.s.selected_pet = '0'
        self.s.show('Mascotas')
        self.out = Path('previews/portrait-arches'); self.out.mkdir(parents=True, exist_ok=True)
        Window.size = (390, 844)
        Clock.schedule_once(self.press, .4)

    def press(self, _):
        self.row = next(w for w in self.s.content.children if w.__class__.__name__ == 'HomePetRow')
        assert self.row.compress_on_press
        self.press_checks = 0
        self.row.state = 'down'
        Clock.schedule_once(self.pressed, .15)

    def pressed(self, _):
        if abs(self.row.visual_scale-.985) >= .001:
            self.press_checks += 1
            assert self.press_checks < 15, (self.row.visual_scale, self.row.state)
            Clock.schedule_once(self.pressed, .1)
            return
        self.row.state = 'normal'
        self.release_checks = 0
        Clock.schedule_once(self.released, .2)

    def released(self, _):
        if self.row.visual_scale != 1:
            self.release_checks += 1
            assert self.release_checks < 15
            Clock.schedule_once(self.released, .1)
            return
        assert self.row.visual_scale == 1
        self.root.export_to_png(str(self.out/'mascotas-390.png'))
        self.tap_row = max((w for w in self.s.content.children if w.__class__.__name__ == 'HomePetRow'), key=lambda w: w.y)
        self.tap_row.callback = self.tap_callback = Mock()
        self.touch = Touch(*self.tap_row.center)
        self.touch.down(); self.touch.up()
        Clock.schedule_once(self.tapped, .4)

    def tapped(self, _):
        self.tap_callback.assert_called_once()
        self.tap_callback.reset_mock()
        self.touch = Touch(*self.tap_row.center)
        self.touch.down()
        self.touch.drag(self.tap_row.center_x, self.tap_row.center_y+80)
        self.touch.up()
        Clock.schedule_once(self.scrolled, .4)

    def scrolled(self, _):
        self.tap_callback.assert_not_called()
        assert self.tap_row.visual_scale == 1 and self.tap_row.state == 'normal'
        Window.size = (320, 640)
        self.original_form = self.s.form
        def capture(*args, **kwargs):
            self.modal, self.entries = self.original_form(*args, **kwargs)
            return self.modal, self.entries
        with patch.object(self.s, 'form', side_effect=capture):
            self.s.register_pet(pet=self.s.data['pets'][0])
        self.preview = next(w for w in self.modal.walk() if w.__class__.__name__ == 'PetFormPreview')
        self.open_checks = 0
        self.entries['breed'].is_open = True
        Clock.schedule_once(self.opened, .2)

    def opened(self, _):
        if self.entries['breed'].arrow_angle != 180:
            self.open_checks += 1
            assert self.open_checks < 15, (self.entries['breed'].arrow_angle, self.entries['breed'].is_open)
            Clock.schedule_once(self.opened, .1)
            return
        self.entries['breed'].is_open = False
        for breed in ('Persa', 'Bengalí', 'Siamés'):
            self.entries['breed'].text = breed
        self.preview_checks = 0
        Clock.schedule_once(self.previewed, .2)

    def previewed(self, _):
        portrait = self.preview.ids.portrait
        if portrait.opacity != 1 or self.entries['breed'].arrow_angle != 0:
            self.preview_checks += 1
            assert self.preview_checks < 15
            Clock.schedule_once(self.previewed, .1)
            return
        assert portrait.breed == 'Siamés' and portrait.opacity == 1
        assert self.entries['breed'].arrow_angle == 0
        self.modal.export_to_png(str(self.out/'preview-320.png'))
        self.s.motion_enabled = lambda: False
        self.entries['kind'].text = 'Reptil'
        assert portrait.kind == 'Reptil' and portrait.opacity == 1
        avatar = next(w for w in portrait.walk() if w.__class__.__name__ == 'ViewPetAvatar')
        assert avatar.fallback_icon == 'snake' and not avatar.portrait_source
        self.entries['kind'].is_open = True
        assert self.entries['kind'].arrow_angle == 180
        self.entries['kind'].is_open = False
        assert self.entries['kind'].arrow_angle == 0
        self.s.motion_enabled = lambda: True
        self.entries['kind'].text = 'Gato'
        self.entries['breed'].text = 'Persa'
        self.entries['breed'].is_open = True
        self.dropdown = self.entries['breed']._dropdown
        self.modal.dismiss(animation=False)
        Clock.schedule_once(self.dismissed, .1)

    def dismissed(self, _):
        assert self.dropdown.parent is None
        assert not self.entries['breed'].is_open and self.entries['breed'].arrow_angle == 0
        assert self.preview.ids.portrait.opacity == 1
        self.preview.ids.portrait.opacity = .8
        self.entries['breed'].arrow_angle = 25
        Clock.schedule_once(self.closed_idle, .25)

    def closed_idle(self, _):
        assert self.preview.ids.portrait.opacity == .8
        assert self.entries['breed'].arrow_angle == 25
        self.preview.ids.portrait.opacity = 1
        self.entries['breed'].arrow_angle = 0
        self.s.motion_enabled = lambda: False
        self.s.show('Mascotas')
        row = next(w for w in self.s.content.children if w.__class__.__name__ == 'HomePetRow')
        row.state = 'down'
        assert row.visual_scale == 1
        row.state = 'normal'
        self.s.motion_enabled = lambda: True
        row.state = 'down'
        self.s.content.remove_widget(row)
        assert row.visual_scale == 1
        self.template_modal, _ = self.s.form('Ideas', [('name', 'Nombre', '')], lambda _: None,
                                              templates={'Paseo': {'name': 'Paseo'}}, persist=False)
        self.template = next(w for w in self.template_modal.walk() if w.__class__.__name__ == 'FormTemplate')
        self.template.is_open = True
        self.template_modal.dismiss(animation=False)
        Clock.schedule_once(self.template_closed, .1)

    def template_closed(self, _):
        assert not self.template.is_open and self.template.arrow_angle == 0
        assert self.template._dropdown.parent is None
        self.stop(); self.tmp.cleanup()
        print('PASS: tap/scroll, card press/release/cancel, rapid preview, dropdowns, modal cleanup, species icons and reduced motion')


if __name__ == '__main__': Check().run()
