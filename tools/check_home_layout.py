"""Representative home/menu layouts using temporary data and no account requests."""
import os,sys
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS']='1'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from screens.views import ViewText
from services.store import empty_data,pet_values,care_now
from datetime import timedelta

class Check(MiMascotaApp):
 def build(self):
  self.temp=TemporaryDirectory()
  with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'),patch('screens.home.Supabase',return_value=Mock(user=None,configured=False,config={})):
   return super().build()
 def on_start(self):
  self.s=self.root.get_screen('home')
  self.s.mobile=Mock(configured=True)
  self.out=Path('previews/home-layout');self.out.mkdir(parents=True,exist_ok=True)
  self.original=self.s.dialog
  def dialog(*args,**kw):
   modal,card=self.original(*args,**kw);self.modal,self.card=modal,card;return modal,card
  self.s.dialog=dialog
  Clock.schedule_once(self.open_menu,.5)
 def open_menu(self,_):
  self.s.notice_preferences()
  Clock.schedule_once(self.menu,.5)
 def menu(self,_):
  self.modal.export_to_png(str(self.out/'notifications.png'))
  header=self.card.children[-1]
  gap=self.card.top-header.top
  assert abs(gap-dp(22))<dp(3),f'Blank space above menu: {gap/dp(1):.0f}dp'
  self.modal.dismiss()
  if '--menu-only' in sys.argv:self.stop();print('PASS compact notification dialog');return
  self.states=iter([(width,state) for width in (390,320) for state in ('empty','pets','long')])
  self.next(None)
 def next(self,_):
  item=next(self.states,None)
  if item is None:
   self.s.register_pet();Clock.schedule_once(self.form,.5);return
  self.width,self.state=item
  Window.size=(self.width,844 if self.width==390 else 640)
  self.s.data=empty_data()
  if self.state!='empty':
   for i,(name,kind) in enumerate([('Luna','Perro'),('Milo','Gato')]):
    pet=pet_values(dict(name=name if self.state=='pets' else name+' de la familia Rodríguez Fernández',kind=kind,breed='Golden retriever' if i==0 else 'Europeo',age='3 años'))
    pet['id']=str(i);self.s.data['pets'].append(pet)
   due=(care_now(self.s.data)+timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
   self.s.data['routines']=[dict(id='care',pet='0',title='Paseo de Luna' if self.state=='pets' else 'Revisión y control veterinario de Luna',detail='',due_at=due,time=due,kind='Cuidado',icon='walk',repeat='No',done=False)]
  self.s.show('Inicio');Clock.schedule_once(self.capture,.5)
 def capture(self,_):
  text=[w.text for w in self.s.content.walk() if isinstance(w,ViewText)]
  assert not any(t in text for t in ('Siempre cerca.','TU ESPACIO','HOY EN UN VISTAZO'))
  for w in self.s.content.walk():
   if isinstance(w,ViewText) and w.wrap:assert w.height+1>=w.texture_size[1],w.text
  self.s.export_to_png(str(self.out/f'home-{self.state}-{self.width}.png'))
  Clock.schedule_once(self.next,.1)
 def form(self,_):
  assert self.modal.height>=Window.height*.8,'Pet form lost its available space'
  assert self.card.children[-1].top>=self.card.top-dp(26),'Form title lost top alignment'
  self.modal.export_to_png(str(self.out/'pet-form.png'));self.modal.dismiss()
  self.s.account_settings();Clock.schedule_once(self.settings,.5)
 def settings(self,_):
  assert self.card.children[-1].top>=self.card.top-dp(26),'Settings title lost top alignment'
  self.modal.export_to_png(str(self.out/'account-settings.png'));self.modal.dismiss()
  self.temp.cleanup();self.stop();print('PASS home at 390/320px, compact menus, long text and scrollable pet form')
Check().run()
