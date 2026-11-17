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
        s.cloud = Mock(user={'id': THREAD}, configured=False, config={})
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
        self.ux_patcher=patch('screens.ux.QrInbox',return_value=self.client)
        self.ux_patcher.start()
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
        assert bell.width >= 48 and bell.height >= 48
        self.screen.shell.export_to_png(str(self.output / 'home-bell-390.png'))
        assert self.screen.active == 'Avisos'
        from screens.ux import UxPress
        self.client.mark_read.assert_not_called()
        next(w for w in self.screen.content.walk() if isinstance(w,UxPress) and w.context.get('title')=='Luna').dispatch('on_release')
        Clock.schedule_once(self.conversation,.7)

    def conversation(self, _):
        assert self.screen.active == 'Conversación'
        self.client.mark_read.assert_called_with(THREAD,MESSAGE)
        literal=next(w for w in self.screen.content.walk() if isinstance(w,ViewText) and w.text.startswith('[b]'))
        assert not literal.markup and literal.height > 100
        self.screen.export_to_png(str(self.output/'conversation-390.png'))
        composer=next(w for w in self.screen.content.children if 'message' in w.ids)
        composer.ids.message.text='Gracias, voy a buscarla.\nNos vemos en la plaza.'
        self.client.reply.return_value=dict(self.result,status='contacted')
        self.screen.send_inline_reply(THREAD,composer)
        assert self.client.reply.call_args.args[0]==THREAD
        assert self.client.reply.call_args.args[1].startswith('Gracias')
        assert self.screen._qr_reply_draft is None
        Window.size=(320,640)
        Clock.schedule_once(self.finish,.5)

    def finish(self,_):
        self.screen.export_to_png(str(self.output/'conversation-320.png'))
        assert all(w.width<=320 for w in self.screen.content.walk() if isinstance(w,ViewText))
        self.screen._qr_reply_draft=dict(owner=THREAD,thread=THREAD,text='privado',request=THREAD)
        self.screen.cloud.user=None
        self.screen.refresh_qr_badge()
        assert self.screen._qr_reply_draft is None
        self.patcher.stop();self.ux_patcher.stop()
        self.stop();self.temp.cleanup()
        print('PASS: current notice page, literal conversation, inline reply, read receipt, 390/320 and owner cleanup')


if __name__ == '__main__':
    Check().run()
