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
from screens.views import ViewText,ViewAction

class Check(MiMascotaApp):
 def build(self):
  self.temp=TemporaryDirectory()
  with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'):
   return super().build()
 def on_start(self):
  self.s=self.root.get_screen('home')
  self.s.cloud=Mock(user={'id':'fixture'},configured=False,config={})
  self.s.mobile=Mock(configured=False)
  self.states=iter([(width,state) for width in (390,320) for state in ('none','pending','active','cancelled')])
  self.out=Path('previews/billing');self.out.mkdir(parents=True,exist_ok=True)
  Clock.schedule_once(self.next,.4)
 def next(self,_):
  item=next(self.states,None)
  if item is None:
   self.s._billing_modal.dismiss();self.stop();print('PASS: billing states at 390/320px, scroll and no checkout opened');return
  self.width,self.state=item
  Window.size=(self.width,844 if self.width==390 else 640)
  self.s.render_subscription({'id':'luna','name':'Luna de la familia Rodríguez'},dict(state=self.state,paid_until='2026-12-13T12:00:00+00:00' if self.state in ('active','cancelled') else None,checkout_url='https://www.mercadopago.cl/subscriptions/checkout?fixture' if self.state=='pending' else None))
  Clock.schedule_once(self.capture,.45)
 def capture(self,_):
  modal=self.s._billing_modal
  assert modal.height<Window.height
  for widget in modal.walk():
   if isinstance(widget,ViewText) and widget.wrap:
    assert widget.height+1>=widget.texture_size[1],widget.text
  if self.state=='pending':
   assert any(isinstance(w,ViewAction) and w.text=='Comprobar pago' for w in modal.walk())
  modal.export_to_png(str(self.out/f'{self.state}-{self.width}.png'))
  Clock.schedule_once(self.next,.05)
Check().run()
