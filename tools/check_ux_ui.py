"""Account/notices/QR usability checks with synthetic data, no real cloud requests."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS']='1'
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from kivy.clock import Clock
from kivy.core.window import Window
from screens.views import ViewText,ViewAction
from screens.ux import UxPress
from services.store import pet_values
from datetime import datetime,timedelta,timezone
from tests.test_qr_inbox import conversation,THREAD,MESSAGE


class Check(MiMascotaApp):
    def build(self):
        self.temp=TemporaryDirectory()
        with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'):
            return super().build()

    def on_start(self):
        self.s=self.root.get_screen('home')
        self.s._backup_clock.cancel()
        self.s._qr_poll.cancel()
        self.s._notice_timer.cancel()
        self.output=Path('previews/ux');self.output.mkdir(parents=True,exist_ok=True)
        self.s.cloud=Mock(user={'id':THREAD,'email':'familia@example.invalid'})
        self.s.cloud.restore_session.return_value=False
        self.s.cloud.site_url='https://mi-mascota-web.vercel.app'
        self.s.mobile=Mock(configured=True)
        self.s.contact_profile=lambda: {'name':'María Rodríguez'}
        self.s.network=lambda operation,callback: callback(operation())
        self.result=conversation()
        self.result['messages'][0]['text']='Encontré a Luna junto a la plaza. Está bien y le di agua.'
        self.result['can_reply']=True
        self.client=Mock()
        self.client.read.return_value=self.result
        self.client.mark_read.return_value=self.result
        self.client.reply.return_value=self.result
        self.client.list.return_value={'unread':1,'next_cursor':None,'threads':[dict(id=THREAD,pet_id='fixture-pet',pet_name='Luna',status='open',archived=False,unread=1,updated_at=self.result['expires_at'],preview=self.result['messages'][0]['text'])]}
        self.patches=[patch('screens.ux.QrInbox',return_value=self.client),patch('screens.qr_inbox.QrInbox',return_value=self.client)]
        for p in self.patches:p.start()
        self.s._qr_owner=THREAD
        Clock.schedule_once(self.open_account,.3)

    def open_account(self,_):
        self.s.account()
        Clock.schedule_once(self.account,.6)

    def labels(self):
        return [w.text for w in self.s.content.walk() if isinstance(w,ViewText)]

    def shot(self,name):
        self.s.content.export_to_png(str(self.output/(name+'.png')))

    def account(self,_):
        assert self.s.active=='Cuenta'
        labels=self.labels()
        assert 'María Rodríguez' in labels and 'familia@example.invalid' in labels
        assert 'Exportar copia' not in labels and 'Mis datos' not in labels
        assert any(w.icon=='pencil-outline' for w in self.s.content.walk() if isinstance(w,ViewAction))
        assert self.s.shell.width==Window.width
        self.shot('account-390')
        self.s.notifications_center()
        Clock.schedule_once(self.notices,.7)

    def notices(self,_):
        assert self.s.active=='Avisos'
        if self.s._notice_loading:
            Clock.schedule_once(self.notices,.3)
            return
        assert self.result['messages'][0]['text'] in self.labels(), (self.s._notice_error, self.s._notice_rows, self.labels())
        assert 'Actualizar' not in self.labels() and 'Ver archivados' not in self.labels()
        entry=next(w for w in self.s.content.walk() if isinstance(w,UxPress) and w.context.get('title')=='Luna')
        self.shot('notices-390')
        entry.dispatch('on_release')
        Clock.schedule_once(self.chat,.6)

    def chat(self,_):
        assert self.s.active=='Conversación'
        self.client.mark_read.assert_called_with(THREAD,MESSAGE)
        composer=next(w for w in self.s.content.children if 'message' in w.ids)
        assert composer.ids.message.multiline
        composer.ids.message.text='Gracias, voy a buscarla.'
        self.s.qr_conversation_panel(self.result)
        composer=next(w for w in self.s.content.children if 'message' in w.ids)
        assert composer.ids.message.text=='Gracias, voy a buscarla.', 'Refresh discarded reply draft'
        self.s.send_inline_reply(THREAD,composer)
        self.client.reply.assert_called_once()
        assert self.s._qr_reply_draft is None, 'Sent reply reappeared as draft'
        Clock.schedule_once(self.qr,.5)

    def qr(self,_):
        self.shot('chat-390')
        now=datetime.now(timezone.utc)
        pet=pet_values({'name':'Luna','kind':'Perro'});pet['id']='fixture-pet'
        tag={'status':'active','scan_code':THREAD,'url':'https://mi-mascota-web.vercel.app/q/'+THREAD,
             'created_at':now.isoformat(),'expires_at':(now+timedelta(days=14)).isoformat()}
        self.s.public_tag_panel(pet,tag)
        Clock.schedule_once(self.large_qr,.5)

    def large_qr(self,_):
        from screens.views import ViewImage
        qr=next(w for w in self.s.content.walk() if isinstance(w,ViewImage))
        assert qr.height>290 and qr.height==qr.width
        self.shot('qr-390')
        Window.size=(320,640)
        Clock.schedule_once(self.small,.5)

    def small(self,_):
        self.s.show('Cuenta')
        Clock.schedule_once(self.finish,.5)

    def finish(self,_):
        self.shot('account-320')
        assert self.s.shell.width==Window.width
        assert all(w.width<=320 for w in self.s.content.walk() if isinstance(w,ViewText))
        self.s.cloud.user=None
        self.s.refresh_qr_badge()
        assert not self.s._notice_rows
        self.s.show('Inicio')
        assert 'Guarda tus mascotas en tu cuenta' in self.labels()
        for p in self.patches:p.stop()
        self.stop();self.temp.cleanup()
        print('PASS: account hierarchy, pencil, direct notice list, preview/date row, inline reply, read receipt, 390/320px, guest copy and logout cleanup.')


if __name__=='__main__':Check().run()
