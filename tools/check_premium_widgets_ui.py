"""Offline widget lifecycle, narrow layout and real Kivy screenshot checks."""
import os
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from screens.views import ViewCard, ViewText, load_views, view
from screens.premium import PersonalTag, PremiumAccountButton, PremiumWelcome, register


class Check(App):
    def build(self):
        register()
        load_views()
        Window.clearcolor = (1, 1, 1, 1)
        return ViewCard(bg='#FFFFFF', shadow=False, radius=0, adaptive=False, padding=16)

    def on_start(self):
        self.motion = patch('screens.premium.interface_motion', return_value=True)
        self.motion.start()
        self.out = Path('previews/premium-widgets')
        self.out.mkdir(parents=True, exist_ok=True)
        self.states = iter((390, 320))
        Clock.schedule_once(self.next, .1)

    def next(self, *_):
        width = next(self.states, None)
        if width is None:
            self.lifecycle()
            return
        self.width = width
        Window.size = width, 844
        self.root.clear_widgets()
        self.button = PremiumAccountButton(icon='account-outline', text='Mi perfil', premium=True)
        self.root.add_widget(self.button)
        self.hero = view('PremiumHero', name='Milo' if width == 390 else 'María José de los Ángeles', source='assets/chapa-personalizable.png')
        self.root.add_widget(self.hero)
        self.welcome = view('PremiumWelcome', name='María José de los Ángeles', kind='Perro', breed='Beagle', date='17 de diciembre', renewal=width == 320)
        self.root.add_widget(self.welcome)
        Clock.schedule_once(self.capture, .5)

    def capture(self, *_):
        tag = next(w for w in self.hero.walk() if isinstance(w, PersonalTag))
        assert tag._name_size[0] <= min(tag.size) * .59 + 1
        original = tag.name
        tag.name = 'ÁÉÑ語' * 12
        assert tag._name_size[0] <= min(tag.size) * .59 + 1
        tag.name = original
        assert self.button._ring_event is not None
        assert self.welcome.phase > 0
        labels = [w.text for w in self.welcome.walk() if isinstance(w, ViewText)]
        assert ('¡Premium renovado!' if self.width == 320 else '¡Ya es Premium!') in labels
        self.root.export_to_png(str(self.out / f'premium-{self.width}.png'))
        Clock.schedule_once(self.next, .1)

    def lifecycle(self):
        self.button.motion_active = False
        assert self.button._ring_event is None
        self.button.motion_active = True
        self.button.premium = False
        assert self.button._ring_event is None
        self.button.premium = True
        with patch('screens.premium.interface_motion', return_value=False):
            self.button.refresh_motion()
            self.welcome.present()
            assert self.button._ring_event is None
            assert self.welcome.phase == 1
            self.root.export_to_png(str(self.out / 'reduced-motion-320.png'))
        self.root.clear_widgets()
        assert self.button._ring_event is None
        from kivy.animation import Animation
        assert not any(a.have_properties_to_animate(self.welcome) for a in Animation._instances)
        self.motion.stop()
        self.stop()
        print('PASS: 390/320, Unicode fit, Premium lifecycle, reduced motion, welcome cancellation')


if __name__ == '__main__':
    Check().run()
