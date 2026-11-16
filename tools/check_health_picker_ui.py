"""Real health selection with duplicate names, synthetic data and screenshots."""
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
from main import MiMascotaApp
from screens.views import ViewAction, ViewText
from services.store import empty_data, pet_values


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.temp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=Mock(user=None, configured=False, config={})):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.mobile = Mock(configured=False)
        self.s.data = empty_data()
        self.pets = [dict(pet_values(dict(name='Julián', kind=kind, breed=breed, weight='4.5')), id=str(i))
                     for i, (kind, breed) in enumerate((('Gato', 'Europeo'), ('Perro', 'Mestizo')))]
        self.s.data['pets'] = self.pets
        self.s.selected_pet = '0'
        self.s.data['events'] = [dict(id='event', pet='1', title='Control', date='2026-11-16 10:00', detail='', kind='Control')]
        self.output = Path('previews/editorial'); self.output.mkdir(parents=True, exist_ok=True)
        Window.size = (320, 640)
        Clock.schedule_once(lambda _: self.s.show('Salud'), .3)
        Clock.schedule_once(self.pick, .8)

    def labels(self):
        return [w.text for w in self.s.content.walk() if isinstance(w, ViewText)]

    def pick(self, _):
        assert self.s.width == Window.width, (self.s.size, self.root.size, Window.size)
        assert not any(w.__class__.__name__ == 'HealthSelector' for w in self.s.content.walk()), 'Old numbered selector remains'
        assert self.labels().count('Julián') == 1
        change = next(w for w in self.s.content.walk() if isinstance(w, ViewAction) and w.text == 'Cambiar mascota')
        change.dispatch('on_release')
        Clock.schedule_once(self.select_duplicate, .3)

    def select_duplicate(self, _):
        modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        self.root.export_to_png(str(self.output/'selector-320.png'))
        modal.export_to_png(str(self.output/'selector-dialogo-320.png'))
        rows = [w for w in modal.walk() if w.__class__.__name__ == 'HealthPetOption']
        assert len(rows) == 2
        for row in rows:
            portrait = next(w for w in row.walk() if w.__class__.__name__ == 'ViewPetAvatar')
            assert portrait.kind == row.context['kind'], 'Portrait species did not update'
            if row.context['selected']:
                from kivy.core.text import Label as CoreLabel
                from kivymd.icon_definitions import md_icons
                icon = next(w for w in row.walk() if isinstance(w, ViewText) and w.text == md_icons['check-circle'])
                natural = CoreLabel(text=icon.text, font_name=icon.font_name, font_size=icon.font_size)
                natural.refresh()
                assert icon.width >= natural.texture.width, 'Selected check is clipped horizontally'
        next(row for row in rows if row.context['kind'] == 'Perro').dispatch('on_release')
        Clock.schedule_once(self.selected, .3)

    def selected(self, _):
        assert self.s.selected_pet == '1', 'Duplicate names selected the wrong id'
        assert '1 registro en su historial' in self.labels()
        self.root.export_to_png(str(self.output/'salud-varias-320.png'))
        with patch.object(self.s, 'export_health_report') as export:
            button = next(w for w in self.s.content.walk() if isinstance(w, ViewAction) and w.text == 'Compartir PDF')
            button.dispatch('on_release')
            export.assert_called_once()
        self.s.change_health_pet()
        next(w for w in Window.children if hasattr(w, 'dismiss')).dismiss(animation=False)
        assert self.s.selected_pet == '1'
        self.s.data['pets'] = [self.pets[1]]
        self.s.show('Salud')
        Clock.schedule_once(self.single, .3)

    def single(self, _):
        assert 'Cambiar mascota' not in self.labels()
        self.root.export_to_png(str(self.output/'salud-una-320.png'))
        self.s.data['pets'][0]['name'] = 'Julián de la familia Rodríguez Fernández'
        self.s.show('Salud')
        Clock.schedule_once(self.finish, .3)

    def finish(self, _):
        for w in self.s.content.walk():
            if isinstance(w, ViewText) and w.wrap:
                assert w.height + 1 >= w.texture_size[1], w.text
        self.root.export_to_png(str(self.output/'salud-largo-320.png'))
        self.s.profile(self.s.data['pets'][0])
        Clock.schedule_once(self.profile, .4)

    def profile(self, _):
        modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        scroll = next(w for w in modal.walk() if w.__class__.__name__ == 'AccountScroll')
        assert scroll.height > 0 and scroll.top <= modal.top
        modal.export_to_png(str(self.output/'perfil-320.png'))
        modal.dismiss(animation=False)
        self.stop(); self.temp.cleanup()
        print('PASS: integrated health picker, duplicate ids, cancel, single pet, PDF and long name at 320px')


if __name__ == '__main__': Check().run()
