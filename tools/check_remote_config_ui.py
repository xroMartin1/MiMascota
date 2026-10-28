"""Real Kivy layout and public tip; no login, private data or notifications."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from services.cloud import CloudError
from services.remote_config import RemoteConfig


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.temp.name)/'guest.json'):
            return super().build()

    def on_start(self):
        self.screen = self.root.get_screen('home')
        self.screen.cloud.restore_session = lambda: False
        self.attempts = 0
        Clock.schedule_once(self.wait_tip, .8)

    def wait_tip(self, _):
        self.attempts += 1
        if self.screen._tip_running or self.screen.remote_config.source != 'remote':
            assert self.attempts < 35, 'Remote tip did not load'
            Clock.schedule_once(self.wait_tip, 1)
            return
        self.remote_text = self.screen.remote_config.message
        self.output = Path(__file__).resolve().parents[1]/'previews'/'remote-config'
        self.output.mkdir(parents=True,exist_ok=True)
        Clock.schedule_once(self.capture_wide,.4)

    def capture_wide(self, _):
        card = self.screen._tip_view
        assert card.ids.tip_text.text == self.remote_text
        assert card.ids.tip_status.text == 'Actualizado en línea'
        assert card.ids.tip_text.height >= card.ids.tip_text.texture_size[1]
        card.export_to_png(str(self.output/'consejo-390.png'))
        Window.size = (320,844)
        Clock.schedule_once(self.capture_narrow,.5)

    def capture_narrow(self, _):
        card = self.screen._tip_view
        assert card.ids.tip_text.height >= card.ids.tip_text.texture_size[1]
        card.export_to_png(str(self.output/'consejo-320.png'))
        restored = RemoteConfig(self.screen.cloud,self.screen.remote_config.path)
        with patch.object(self.screen.cloud,'request',side_effect=CloudError('Sin conexión')):
            assert not restored.refresh()
        assert restored.message == self.remote_text and restored.source == 'cache'
        self.screen.remote_config = restored
        self.screen.show('Inicio')
        Clock.schedule_once(self.capture_offline,.4)

    def capture_offline(self, _):
        card = self.screen._tip_view
        assert card.ids.tip_status.text == 'Último consejo guardado'
        card.export_to_png(str(self.output/'consejo-sin-conexion.png'))
        for page in ('Mascotas','Rutina','Salud','Cuenta','Inicio'):
            self.screen.show(page)
        print('PASS: UI 390/320, consejo remoto real, recuperación sin conexión y navegación.')
        self.stop()


Check().run()
