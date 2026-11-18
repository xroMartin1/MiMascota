"""Check persistent tab travel, interruption, resize and reduced motion in Kivy."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.views import ViewText


class Check(MiMascotaApp):
    def build(self):
        self.tmp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.tmp.name) / 'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.motion_enabled = lambda: True
        self.s.network = lambda *args, **kwargs: None
        self.buttons = tuple(self.s.nav.children)
        self.waits = 0
        self.out = Path('previews/navigation-motion')
        self.out.mkdir(parents=True, exist_ok=True)
        Window.size = (390, 844)
        Clock.schedule_once(self.travel, .4)

    def button(self, title):
        return next(b for b in self.buttons if b.text == title)

    def wait_for(self, condition, callback):
        if condition:
            self.waits += 1
            assert self.waits < 25, callback.__name__
            Clock.schedule_once(callback, .1)
            return True
        self.waits = 0
        return False

    def aligned(self, title):
        nav, button = self.s.nav, self.button(title)
        assert abs(nav.indicator_pos[0] - button.x) < .1
        assert abs(nav.indicator_pos[1] - button.y) < .1
        assert tuple(nav.indicator_size) == tuple(button.size)
        assert [b.text for b in self.buttons if b.context['selected']] == [title]

    def travel(self, _):
        if self.wait_for(self.s.nav.width != Window.width or self.button('Inicio').width < 48, self.travel):
            return
        self.aligned('Inicio')
        self.start_x = self.s.nav.indicator_pos[0]
        self.s.show('Salud')
        assert tuple(self.s.nav.children) == self.buttons, 'Navigation buttons rebuilt'
        assert self.s.nav.indicator_pos[0] == self.start_x, 'Indicator teleported'
        assert any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances)
        Clock.schedule_once(self.interrupt, .06)

    def interrupt(self, elapsed):
        nav = self.s.nav
        assert self.start_x < nav.indicator_pos[0] < self.button('Salud').x, (self.start_x, nav.indicator_pos, self.button('Salud').x, elapsed)
        self.root.export_to_png(str(self.out / 'travel-390.png'))
        current_x = nav.indicator_pos[0]
        self.s.show('Mascotas')
        assert nav.indicator_pos[0] == current_x, 'Interrupted animation jumped'
        Clock.schedule_once(self.settled, .35)

    def settled(self, _):
        if self.wait_for(any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances), self.settled):
            return
        self.aligned('Mascotas')
        self.s.show('Chapa')
        Window.size = (320, 640)
        Clock.schedule_once(self.resized, .4)

    def resized(self, _):
        if self.wait_for(self.s.nav.width != Window.width, self.resized):
            return
        self.aligned('Chapa')
        assert not any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances)
        for b in self.buttons:
            label = next(w for w in b.children if isinstance(w, ViewText) and w.text == b.text)
            assert not label.is_shortened, b.text
            assert b.width >= 48 and b.height >= 48
        self.root.export_to_png(str(self.out / 'chapa-320.png'))
        self.s.motion_enabled = lambda: False
        self.s.show('Rutina')
        self.aligned('Rutina')
        assert not any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances)
        self.s.show('Cuenta')
        assert not self.s.nav.indicator_visible
        self.s.show('Inicio')
        self.aligned('Inicio')
        self.s.motion_enabled = lambda: True
        self.s.show('Salud')
        self.s.motion_enabled = lambda: False
        self.s.show('Salud')
        self.aligned('Salud')
        assert not any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances)
        self.s.show('Mascotas')
        self.aligned('Mascotas')
        assert not any(a.have_properties_to_animate(self.s.nav) for a in Animation._instances)
        self.s.show('Cuenta')
        self.s.public_tag_panel({'id': 'preview', 'name': 'Luna'}, None)
        self.aligned('Chapa')
        self.stop()
        self.tmp.cleanup()
        print('PASS: persistent navigation, real travel, rapid reversal, 320px resize, labels, auxiliary pages and reduced motion')


if __name__ == '__main__':
    Check().run()



