"""Verificación Kivy real con nube simulada; no altera cuentas ni inicia pruebas remotas."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS'] = '1'
from datetime import datetime, timedelta, timezone
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
from services.store import pet_values


class PublicQrCheck(MiMascotaApp):
    def build(self):
        self.tmp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.tmp.name) / 'guest.json'):
            return super().build()

    def on_start(self):
        self.s = self.root.get_screen('home')
        self.output = Path(os.environ['MIMASCOTA_PREVIEW_DIR'])
        self.output.mkdir(parents=True, exist_ok=True)
        Window.size = (390, 844)
        pet = pet_values(dict(name='Max', kind='Perro', breed='', age='', weight='', chip=''))
        pet['id'] = 'fixture-max'
        pet['qr_contact'] = dict(name='Familia de Max', phone='+56900000000', city='', share_phone=True)
        self.s.data['pets'].append(pet)
        self.pet = pet
        self.s.cloud.set_session(dict(access_token='fake', refresh_token='fake', user={
            'id': '00000000-0000-0000-0000-000000000001', 'email': 'fixture@example.com'}))
        self.s.cloud.upload = Mock(return_value={'revision': 1})
        self.s.network = lambda operation, callback: callback(operation())
        now = datetime.now(timezone.utc)
        self.tag = dict(scan_code='00000000-0000-4000-8000-000000000000', created_at=now.isoformat(),
                        expires_at=(now + timedelta(days=14)).isoformat(), status='active',
                        url='https://mi-mascota-web.vercel.app/q/00000000-0000-4000-8000-000000000000')
        self.client = Mock()
        self.client.existing.return_value = None
        self.client.manage.return_value = self.tag
        self.patcher = patch('screens.public_tag.PublicChapas', return_value=self.client)
        self.patcher.start()
        Clock.schedule_once(self.open_tag, .4)

    def open_tag(self, _):
        self.s.qr_info(self.pet)
        assert self.s.data['qr_trials'] == {}
        self.client.manage.assert_not_called()
        Clock.schedule_once(self.unissued, .8)

    def modal(self):
        return next(w for w in Window.children if hasattr(w, 'dismiss'))

    def button(self, text):
        return next(w for window in Window.children for w in window.walk()
                    if isinstance(w, ViewAction) and w.text == text)

    def unissued(self, _):
        self.modal().ids.card.export_to_png(str(self.output / 'web-sin-emitir.png'))
        self.button('Crear QR').dispatch('on_release')
        self.s.cloud.upload.assert_not_called()
        self.button('Confirmar').dispatch('on_release')
        self.s.cloud.upload.assert_called_once()
        self.client.manage.assert_called_once_with(self.pet['id'], 'issue')
        assert self.s.public_tag_path(self.pet).exists()
        Clock.schedule_once(self.active, .4)

    def active(self, _):
        self.modal().ids.card.export_to_png(str(self.output / 'web-activa.png'))
        actions = [w.text for w in self.modal().walk() if isinstance(w, ViewAction) and w.text]
        assert set(actions) == {'Ver ficha', 'Editar contacto', 'Más opciones'}
        self.button('Más opciones').dispatch('on_release')
        self.button('Desactivar chapa').dispatch('on_release')
        self.client.manage.return_value = dict(self.tag, status='unavailable')
        self.button('Confirmar').dispatch('on_release')
        assert self.client.manage.call_args.args == (self.pet['id'], 'revoke')
        assert not self.s.public_tag_path(self.pet).exists()
        Window.size = (320, 640)
        Clock.schedule_once(self.revoked, .4)

    def revoked(self, _):
        self.modal().ids.card.export_to_png(str(self.output / 'web-revocada-320.png'))
        self.modal().dismiss(animation=False)
        self.patcher.stop()
        self.stop()
        self.tmp.cleanup()
        print('PASS: opening does not issue; explicit cloud upload, URL QR, revision and revocation. No remote data changed.')


if __name__ == '__main__':
    PublicQrCheck().run()
