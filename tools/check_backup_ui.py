"""Exercise automatic backup and offline edits using a synthetic remote."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS']='1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from services.store import empty_data, pet_values
from services.cloud import CloudError
from kivy.clock import Clock

OWNER='10000000-0000-4000-8000-000000000001'


class FakeCloud:
    configured=True
    config={}
    session_persisted=True
    url='https://fixture.supabase.co'
    user={'id':OWNER,'email':'fixture@example.invalid'}
    def __init__(self):
        self.remote=empty_data()
        self.remote['pets']=[dict(pet_values({'name':'Luna','kind':'Gato'}),id='pet-1')]
        self.revision=3
        self.offline=False
    def restore_session(self): return True
    def request(self,*args,**kwargs): return {'external':{'google':False}}
    def retry_session_cache(self): pass
    def download(self):
        if self.offline: raise CloudError('offline')
        return {'data':deepcopy(self.remote),'revision':self.revision}
    def upload(self, value):
        assert value['cloud_revision']==self.revision
        self.remote=deepcopy(value)
        self.revision+=1
        return {'revision':self.revision}


class Check(MiMascotaApp):
    def build(self):
        self.temp=TemporaryDirectory()
        self.fake=FakeCloud()
        with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'),patch('screens.home.Supabase',return_value=self.fake):
            return super().build()
    def on_start(self):
        self.s=self.root.get_screen('home')
        Clock.schedule_once(self.account,.3)
    def account(self,_):
        self.s.authenticated(True,resumed=True)
        self.s.retry_backup()
        self.wait(self.loaded)
    def wait(self,callback):
        def ready(_):
            if self.s._backup_running:
                Clock.schedule_once(ready,.1)
            else:
                callback()
        Clock.schedule_once(ready,.2)
    def loaded(self):
        assert self.s.data['pets'][0]['name']=='Luna'
        assert self.s.data['cloud_revision']==3
        assert self.s.backup_status=='Todo guardado en tu cuenta'
        self.s.data['pets'][0]['name']='Lunita'
        assert self.s.save()
        self.s.retry_backup()
        self.wait(self.saved)
    def saved(self):
        assert self.fake.remote['pets'][0]['name']=='Lunita'
        assert self.s.data['cloud_revision']==4
        self.fake.offline=True
        self.s.data['pets'][0]['weight']='4'
        assert self.s.save()
        self.s.retry_backup()
        self.wait(self.offline)
    def offline(self):
        assert self.s.data['pets'][0]['weight']=='4'
        assert self.s.store.data['pets'][0]['weight']=='4'
        assert 'recuperar conexión' in self.s.backup_status
        self.fake.offline=False
        self.s.retry_backup()
        self.wait(self.reconnected)
    def reconnected(self):
        assert self.fake.remote['pets'][0]['weight']=='4'
        print('PASS: automatic account load/save, offline local edits and reconnection')
        self.stop()


if __name__=='__main__': Check().run()
