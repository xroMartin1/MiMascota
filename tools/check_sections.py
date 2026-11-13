"""Render the three functional sections with representative, temporary records."""
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
  self.s.mobile=Mock(configured=False)
  self.out=Path(__file__).resolve().parents[1]/'previews/sections';self.out.mkdir(parents=True,exist_ok=True)
  self.states=iter([(width,page) for width in (390,320) for page in ('Mascotas','Rutina','Salud')])
  Clock.schedule_once(self.next,.5)
 def next(self,_):
  item=next(self.states,None)
  if item is None:
   self.temp.cleanup();self.stop();print('PASS sections at 390/320px: wrapped labels and pet/care callbacks');return
  self.width,self.page=item;Window.size=(self.width,844 if self.width==390 else 640)
  self.s.data=empty_data()
  for i,(name,kind) in enumerate([('Luna','Perro'),('Milo','Gato')]):
   pet=pet_values(dict(name=name if self.width==390 else name+' de la familia Rodríguez',kind=kind,breed='Golden retriever' if i==0 else 'Europeo',age='3 años'))
   pet['id']=str(i);self.s.data['pets'].append(pet)
  self.s.selected_pet='0'
  due=(care_now(self.s.data)+timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
  self.s.data['routines']=[dict(id='care'+str(i),pet='0',title=title,detail='',due_at=due,time=due,kind=kind,icon='walk',repeat='No',done=False) for i,(title,kind) in enumerate([('Paseo de la tarde','Cuidado'),('Control veterinario' if self.width==390 else 'Control veterinario y revisión de Luna','Cita')])]
  self.s.show(self.page);Clock.schedule_once(self.capture,.5)
 def capture(self,_):
  for w in self.s.content.walk():
   if isinstance(w,ViewText) and w.wrap:assert w.height+1>=w.texture_size[1],w.text
  self.s.export_to_png(str(self.out/f'{self.page}-{self.width}.png'))
  if self.page=='Mascotas':
   pet_row=next(w for w in self.s.content.children if w.context.get('name')==self.s.data['pets'][0]['name'])
   pet_row.dispatch('on_release')
   modal=next(w for w in Window.children if hasattr(w,'dismiss'))
   assert modal.context['text']==self.s.data['pets'][0]['name']
   modal.dismiss(animation=False)
  if self.page=='Rutina':
   labels=[w.text for w in self.s.content.walk() if isinstance(w,ViewText)]
   assert 'Hecho' in labels and 'Ver detalles' in labels
  Clock.schedule_once(self.next,.1)
Check().run()
