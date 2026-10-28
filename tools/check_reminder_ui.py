"""Abrir el nuevo formulario y publicar con backend simulado, sin datos reales."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from screens.home import HomeScreen
from kivy.clock import Clock
from kivy.core.window import Window
from screens.views import ViewSpinner, ViewAction

class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        self.screen = HomeScreen(data_file=Path(self.temp.name)/'guest.json',name='home')
        from kivymd.uix.screenmanager import MDScreenManager
        manager=MDScreenManager();manager.add_widget(self.screen)
        return manager
    def on_start(self):
        s=self.screen
        s.cloud=Mock();s.cloud.user={'id':'10000000-0000-4000-8000-000000000001'}
        s.cloud.restore_session.return_value=False
        s.mobile=Mock();s.mobile.configured=True
        bridge=Mock();bridge.deviceId.return_value='device';bridge.token.return_value='token'
        s.mobile.native.return_value=(bridge,'activity')
        def request(method,path,payload=None,**kwargs):
            action=(payload or {}).get('action')
            if action=='plan_status': return {'revision':0}
            if action=='plan_save': return {'revision':1}
            if action=='register': return {'registered':True}
            return {'tags':[]}
        s.cloud.request.side_effect=request
        self.errors=[]
        s.message=lambda title,message:self.errors.append((title,message))
        s.reminder_panel()
        modal=next(w for w in Window.children if hasattr(w,'dismiss'))
        spinner=next(w for w in modal.walk() if isinstance(w,ViewSpinner) and tuple(w.values)==('No','Sí'))
        spinner.text='Sí'
        button=next(w for w in modal.walk() if isinstance(w,ViewAction) and w.text=='Guardar recordatorios')
        self.check_attempts=0
        def publish(_):
            button.dispatch('on_release')
            Clock.schedule_once(self.verify,1)
        Clock.schedule_once(publish,.5)
    def verify(self,_):
        s=self.screen
        self.check_attempts+=1
        if getattr(s,'_reminder_running',False) and self.check_attempts<20:
            Clock.schedule_once(self.verify,1)
            return
        assert s.data['reminder_settings']['enabled']
        if s.data['reminder_revision']!=1:
            print('Fixture diagnostics:',self.errors,[call.args[2].get('action') for call in s.cloud.request.call_args_list])
        assert s.data['reminder_revision']==1 and not s.data['reminder_dirty'], (self.errors,[call.args[2].get('action') for call in s.cloud.request.call_args_list])
        assert s.cloud.request.call_args.args[2]['payload']['timezone']=='America/Santiago'
        print('PASS: activation form, explicit zone, own-device registration, publication and local acknowledgement')
        for w in list(Window.children):
            if hasattr(w,'dismiss'):w.dismiss(animation=False)
        self.stop();self.temp.cleanup()
if __name__=='__main__':Check().run()
