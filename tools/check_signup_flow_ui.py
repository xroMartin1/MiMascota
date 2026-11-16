"""Verifica continuación del registro con respuestas simuladas, sin enviar correos."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS'] = '1'
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.views import ViewAction
from services.cloud import CloudError


class SignupCheck(MiMascotaApp):
    def build(self):
        self.tmp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.tmp.name) / 'guest.json'):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.s.cloud.authenticate = Mock(side_effect=[CloudError('email_not_confirmed'), True])
        self.s.authenticated = Mock()
        def network(operation, callback):
            try: callback(operation())
            except CloudError: pass
        self.s.network = network
        Clock.schedule_once(self.open_confirmation, .3)

    def open_confirmation(self, _):
        self.s.confirm_signup_email('fixture@example.com', 'fake-test-password')
        Clock.schedule_once(self.confirm, .4)

    def confirm(self, _):
        modal = next(w for w in Window.children if hasattr(w, 'dismiss'))
        path = Path(os.environ['MIMASCOTA_PREVIEW_DIR'])
        path.mkdir(parents=True, exist_ok=True)
        modal.ids.card.export_to_png(str(path / 'confirmar-correo.png'))
        button = next(w for w in modal.walk() if isinstance(w, ViewAction) and w.text == 'Ya confirmé mi correo')
        button.dispatch('on_release')
        self.s.authenticated.assert_not_called()
        button.dispatch('on_release')
        self.s.authenticated.assert_called_once_with(True)
        self.assert_credentials_not_saved()
        Clock.schedule_once(self.finish, .3)

    def assert_credentials_not_saved(self):
        for path in Path(self.tmp.name).rglob('*.json'):
            assert 'fake-test-password' not in path.read_text(encoding='utf-8')

    def finish(self, _):
        self.stop()
        self.tmp.cleanup()
        print('PASS: unconfirmed email never opens account; after confirmation continues without retyping. No real email sent.')


if __name__ == '__main__': SignupCheck().run()
