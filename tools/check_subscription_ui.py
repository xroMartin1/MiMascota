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
  with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'),patch('screens.home.Supabase',return_value=Mock(user=None,configured=False,config={})):
   return super().build()
 def on_start(self):
  self.s=self.root.get_screen('home')
  self.s.cloud=Mock(user={'id':'fixture'},configured=False,config={},site_url='https://mi-mascota-web.vercel.app')
  self.s.mobile=Mock(configured=False)
  self.states=iter([(width,state) for width in (390,320) for state in ('none','creating','pending','active','rejected','cancelled','expired')])
  self.out=Path('previews/billing');self.out.mkdir(parents=True,exist_ok=True)
  Clock.schedule_once(self.next,.4)
 def next(self,_):
  item=next(self.states,None)
  if item is None:
   self.checkout();return
  self.width,self.state=item
  Window.size=(self.width,844 if self.width==390 else 640)
  self.s.render_subscription({'id':'luna','name':'Luna de la familia Rodríguez'},dict(state=self.state,order_id='order-123',paid_until='2026-12-13T12:00:00+00:00' if self.state in ('active','cancelled') else None,checkout_url='https://mi-mascota-web.vercel.app/pago/webpay?checkout=11111111-1111-4111-8111-111111111111.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' if self.state=='pending' else None))
  Clock.schedule_once(self.capture,.45)
 def capture(self,_):
  modal=self.s._billing_modal
  assert modal.height<Window.height
  texts=[w.text for w in modal.walk() if isinstance(w,ViewText)]
  assert 'Conserva el mismo QR' in texts, 'Premium benefits must be distinct from technical copy'
  assert not any('Mercado Pago' in text or 'Cancelar renovación' in text for text in texts)
  assert ('Premium activo' in texts)==(self.state=='active')
  expected={'active':'Renovar Premium','pending':'Continuar con Webpay','creating':'Actualizar estado'}.get(self.state,'Pagar con Webpay')
  assert any(isinstance(w,ViewAction) and w.text==expected for w in modal.ids.card.children)
  assert 'order-123' not in texts
  assert not any('Referencia de pago' in text or 'no incluida' in text for text in texts)
  assert not any('checkout=' in text for text in texts)
  if self.state in ('active','cancelled'):
   assert any('Disponible hasta el' in text for text in texts)
  for widget in modal.walk():
   if isinstance(widget,ViewText) and widget.wrap:
    assert widget.height+1>=widget.texture_size[1],widget.text
  footer=next(w for w in modal.ids.card.children if isinstance(w,ViewAction))
  assert modal.y<=footer.y and footer.top<=modal.top
  if self.state=='pending':
   assert any(isinstance(w,ViewAction) and w.text=='Actualizar estado' for w in modal.walk())
  modal.export_to_png(str(self.out/f'{self.state}-{self.width}.png'))
  Clock.schedule_once(self.next,.05)
 def checkout(self):
  pet={'id':'luna','name':'Luna'}
  url='https://mi-mascota-web.vercel.app/pago/webpay?checkout=11111111-1111-4111-8111-111111111111.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
  self.s.render_subscription(pet,dict(state='pending',checkout_url=url))
  with patch('screens.billing.webbrowser.open') as opened:
   next(w for w in self.s._billing_modal.walk() if isinstance(w,ViewAction) and w.text=='Continuar con Webpay').dispatch('on_release')
   opened.assert_not_called()
   notice=next(w for w in Window.children if getattr(w,'context',{}).get('text')=='Pago de prueba')
   next(w for w in notice.walk() if isinstance(w,ViewAction) and w.text=='Confirmar').dispatch('on_release')
   opened.assert_called_once_with(url)
  for widget in list(Window.children):
   if hasattr(widget,'dismiss'):widget.dismiss(animation=False)
  from kivy.uix.textinput import TextInput
  for state,button in [('none','Pagar con Webpay'),('active','Renovar Premium')]:
   self.s.render_subscription(pet,dict(state=state))
   with patch.object(self.s,'network') as network,patch('screens.billing.Subscription') as service,patch('screens.billing.webbrowser.open') as opened:
    next(w for w in self.s._billing_modal.walk() if isinstance(w,ViewAction) and w.text==button).dispatch('on_release')
    network.assert_not_called()
    opened.assert_not_called()
    notice=next(w for w in Window.children if getattr(w,'context',{}).get('text')=='Pago de prueba')
    assert not any(isinstance(w,TextInput) for w in notice.walk())
    assert any('nunca tarjetas reales' in w.text for w in notice.walk() if isinstance(w,ViewText))
    next(w for w in notice.walk() if isinstance(w,ViewAction) and w.text=='Confirmar').dispatch('on_release')
    network.assert_called_once()
    network.call_args.args[0]()
    service.return_value.call.assert_called_once_with('luna','create')
    network.call_args.args[1](dict(state='pending',checkout_url=url))
    opened.assert_called_once_with(url)
    assert not any(w.text=='Premium activo' for w in self.s._billing_modal.walk() if isinstance(w,ViewText))
   for widget in list(Window.children):
    if hasattr(widget,'dismiss'):widget.dismiss(animation=False)
  self.stop();self.temp.cleanup()
  print('PASS: 14 billing states, scroll/visible footer, sandbox disclosure before checkout, manual renewal, create payload and no real checkout opened')
Check().run()
