"""Kivy inbox flow with fictional cloud replies; never touches real accounts."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from screens.views import ViewAction, ViewText, ViewTextInput
from kivy.clock import Clock
from kivy.core.window import Window
from tests.test_qr_inbox import conversation, THREAD, MESSAGE


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE', Path(self.temp.name) / 'guest.json'):
            manager = super().build()
        self.screen = manager.get_screen('home')
        return manager

    def on_start(self):
        Window.size = (390, 844)
        self.output = Path(os.environ.get('MIMASCOTA_PREVIEW_DIR', 'previews/qr-inbox'))
        self.output.mkdir(parents=True, exist_ok=True)
        s = self.screen
        s.cloud = Mock(user={'id': THREAD})
        s.busy = False
        s.network = lambda operation, callback: callback(operation())
        self.client = Mock()
        self.result = conversation()
        self.result['messages'][0]['text'] = '[b]Texto literal[/b]\nEncontré a Luna cerca de la plaza. ' * 6
        self.client.read.return_value = self.result
        self.client.mark_read.return_value = self.result
        self.client.list.return_value = dict(unread=3, next_cursor=None, threads=[dict(
            id=THREAD, pet_id='fixture-pet', pet_name='Luna', status='open', archived=False,
            unread=3, updated_at=self.result['expires_at'], preview='Encontré a Luna')])
        self.patcher = patch('screens.qr_inbox.QrInbox', return_value=self.client)
        self.patcher.start()
        s._qr_unread = 3
        s._qr_owner = THREAD
        s.set_qr_badge()
        assert s.shell.ids.qr_unread_badge.text == '3'
        s.notifications_center()
        Clock.schedule_once(self.inbox, .5)

    def modal(self):
        return next(w for w in Window.children if hasattr(w, 'dismiss'))

    def button(self, text):
        return next(w for w in self.modal().walk() if isinstance(w, ViewAction) and w.text == text)

    def inbox(self, _):
        bell = self.screen.shell.ids.notifications
        assert abs(bell.x - bell.parent.x) < 1 and abs(bell.y - bell.parent.y) < 1
        assert bell.top <= self.screen.shell.top and bell.y > self.screen.shell.top - 100
        self.screen.shell.export_to_png(str(self.output / 'home-bell-390.png'))
        self.button('Recordatorios de cuidados')  # Retains the care entry point.
        self.button('Mensajes de tus mascotas · 3 sin leer').dispatch('on_release')
        Clock.schedule_once(self.read, .5)

    def read(self, _):
        self.client.mark_read.assert_not_called()
        self.button('Luna · 3 sin leer').dispatch('on_release')
        Clock.schedule_once(self.conversation, .7)

    def conversation(self, _):
        self.client.mark_read.assert_called_with(THREAD, MESSAGE)
        literal = next(w for w in self.modal().walk() if isinstance(w, ViewText) and w.text.startswith('[b]'))
        assert not literal.markup and literal.height > 100
        self.modal().ids.card.export_to_png(str(self.output / 'conversation-390.png'))
        self.button('Responder').dispatch('on_release')
        Clock.schedule_once(self.reply, .4)

    def reply(self, _):
        inputs = [w for w in self.modal().walk() if isinstance(w, ViewTextInput)]
        assert len(inputs) == 1 and inputs[0].multiline
        inputs[0].text = 'Gracias, voy a buscarla.\nNos vemos en la plaza.'
        self.client.reply.return_value = dict(self.result, status='contacted')
        self.button('Enviar mensaje').dispatch('on_release')
        assert self.client.reply.call_args.args[0] == THREAD
        assert self.client.reply.call_args.args[1].startswith('Gracias')
        assert self.screen._qr_reply_draft is None
        Window.size = (320, 640)
        Clock.schedule_once(self.finish, .5)

    def finish(self, _):
        self.modal().ids.card.export_to_png(str(self.output / 'conversation-320.png'))
        assert all(w.width <= 320 for w in self.modal().walk() if isinstance(w, ViewText))
        self.modal().dismiss(animation=False)
        self.screen._qr_reply_draft = dict(owner=THREAD, thread=THREAD, text='privado', request=THREAD)
        self.screen.cloud.user = None
        self.screen.refresh_qr_badge()
        assert self.screen._qr_reply_draft is None and not self.screen.shell.ids.qr_unread_badge.text
        self.patcher.stop()
        self.stop()
        self.temp.cleanup()
        print('PASS: badge, care entry, inbox, plaintext, rendered read receipt, multiline reply, 320px and logout cleanup.')


if __name__ == '__main__':
    Check().run()
