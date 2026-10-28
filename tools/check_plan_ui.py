"""Render new pages at phone sizes with fixtures; never reads a real account."""
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
from screens.views import ViewText
from services.store import pet_values


class Review(MiMascotaApp):
    def build(self):
        self.temp=TemporaryDirectory()
        with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'):
            return super().build()

    def on_start(self):
        self.s=self.root.get_screen('home')
        self.s._backup_clock.cancel();self.s._qr_poll.cancel();self.s._notice_timer.cancel()
        self.s.cloud=Mock(user={'id':'fixture-owner','email':'familia@example.invalid'},configured=False,config={})
        self.s._qr_owner='fixture-owner'
        self.s.contact_profile=lambda: {'name':'María Rodríguez'}
        self.s.mobile=Mock(configured=False)
        pet=pet_values(dict(name='Luna María de la familia Rodríguez',kind='Perro',age='3 años',weight='12'))
        self.s.data['pets']=[dict(pet,id='fixture')];self.s.selected_pet='fixture'
        self.s.data['events']=[dict(id='event',pet='fixture',title='Control anual',date='2026-10-10 10:30',detail='Peso registrado: 12 kg.',kind='Control')]
        self.s._shared_list=[dict(id='member',name='Luna de la familia Rodríguez',kind='Perro')]
        self.s._shared_pet=dict(id='member',name='Luna',routines=[dict(title='Paseo de la tarde',detail='Treinta minutos junto a la plaza.',time='18:00',done=False)],events=[dict(title='Control anual',date='2026-10-10',detail='Peso registrado: 12 kg.')])
        self.output=Path('previews/plan');self.output.mkdir(parents=True,exist_ok=True)
        self.pages=iter([(width,page) for width in (390,320) for page in ('Cuenta','Salud','Compartidos','Cuidado compartido')])
        Clock.schedule_once(self.next,.4)

    def next(self,_):
        value=next(self.pages,None)
        if value is None:
            self.s.account_settings()
            Clock.schedule_once(self.settings,.4)
            return
        self.width,self.page=value
        Window.size=(self.width,844 if self.width==390 else 640)
        self.s.show(self.page)
        Clock.schedule_once(self.capture,.5)

    def capture(self,_):
        labels=[w.text for w in self.s.content.walk() if isinstance(w,ViewText)]
        if self.page=='Salud':
            assert any(w.icon=='file-export-outline' for w in self.s.content.walk() if hasattr(w,'icon'))
        if self.page=='Compartidos':
            assert 'Tengo una invitación' in labels and 'Compartidas conmigo' in labels
        if self.page=='Cuidado compartido':
            assert any('Acceso de consulta' in t for t in labels)
            assert any('Control anual' in t for t in labels)
        for w in self.s.content.walk():
            if isinstance(w,ViewText) and w.text and w.wrap and w.width>0:
                assert w.height+1>=w.texture_size[1],(self.page,w.text,w.height,w.texture_size)
        self.root.export_to_png(str(self.output/(self.page+'-'+str(self.width)+'.png')))
        Clock.schedule_once(self.next,.1)

    def settings(self,_):
        modal=next(w for w in Window.children if hasattr(w,'dismiss'))
        modal.export_to_png(str(self.output/'ajustes-320.png'))
        labels=[w.text for w in modal.walk() if isinstance(w,ViewText)]
        assert 'Cerrar sesión' in labels and 'Chapa y suscripción' in labels
        assert any(w.__class__.__name__=='AccountScroll' for w in modal.walk())
        modal.dismiss()
        self.s.retry_backup=lambda: None
        self.s.network=lambda operation,callback: callback(operation())
        client=Mock()
        client.call.return_value={'members':[dict(id='fixture-'+str(i),name='Familiar '+str(i+1)) for i in range(3)]}
        with patch('screens.ux.CareShare',return_value=client):
            self.s.care_members(self.s.data['pets'][0])
        Clock.schedule_once(self.members,.4)

    def members(self,_):
        modal=next(w for w in Window.children if hasattr(w,'dismiss'))
        assert any(w.__class__.__name__=='AccountScroll' for w in modal.walk())
        for w in modal.walk():
            if isinstance(w,ViewText) and w.wrap:
                assert w.height+1>=w.texture_size[1], (w.text,w.height,w.texture_size)
        labels=[w.text for w in modal.walk() if isinstance(w,ViewText)]
        assert 'Invitar a una persona' not in labels
        assert any('hasta 3 personas' in text for text in labels)
        modal.export_to_png(str(self.output/'personas-320.png'))
        modal.dismiss()
        with patch.object(self.s,'form') as form, patch.object(self.s,'network') as network:
            self.s.join_care_share()
            submit=form.call_args.args[2]
            assert 'Revisa el código' in submit({'code':'invalid'})
            network.assert_not_called()
        with patch('services.health_report.create_health_report',return_value=Mock()) as create, patch('services.health_report.share_health_report',side_effect=RuntimeError('native chooser unavailable')), patch.object(self.s,'message') as message:
            self.s.prepare_health_report()
            message.assert_called_once()
            assert message.call_args.args[0]=='No se pudo compartir el PDF'
        owner=self.s.cloud.user
        file=Mock()
        def switch_account(*_):
            self.s.cloud.user={'id':'another-account'}
            return file
        with patch('services.health_report.create_health_report',side_effect=switch_account), patch('services.health_report.share_health_report') as share:
            self.s.prepare_health_report()
            share.assert_not_called()
            file.unlink.assert_called_once_with(missing_ok=True)
        self.s.cloud.user=owner
        self.stop();self.temp.cleanup()
        print('PASS: phone layouts, three-member limit, inline code validation, PDF native failure and account-change privacy guard.')


if __name__=='__main__':Review().run()
