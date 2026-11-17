"""Pet hub, daily care, saved history and example-tag turn, using offline fixtures."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS']='1'
import sys
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.views import ViewText,ViewAction
from services.store import empty_data,pet_values


class Check(MiMascotaApp):
    def build(self):
        self.tmp=TemporaryDirectory()
        with patch('screens.home.DATA_FILE',Path(self.tmp.name)/'guest.json'),patch('screens.home.Supabase',return_value=Mock(user=None,configured=False,config={})):
            return super().build()

    def on_start(self):
        self.s=self.root.get_screen('home');self.s.mobile=Mock(configured=False)
        self.s.saved_feedback=Mock()
        self.s.motion_enabled=lambda:True
        self.patches=[patch('screens.features.care_now',return_value=datetime(2026,11,16,12)),patch('services.store.care_now',return_value=datetime(2026,11,16,12))]
        for p in self.patches:p.start()
        self.s.data=empty_data()
        self.pet=dict(pet_values(dict(name='Luna de la familia Rodríguez',kind='Gato',breed='Siamés',age='3',weight='4.5')),id='pet')
        self.s.data['pets']=[self.pet];self.s.selected_pet='pet'
        self.s.data['routines']=[dict(id=str(i),pet='pet',title=title,detail='',kind='Cuidado',repeat='Diaria' if i==0 else 'No',done=False,due_at=date,time=date,icon='paw')
                                  for i,(title,date) in enumerate((('Paseo','2026-11-16 08:00'),('Cepillado','2026-11-16 18:00')))]
        self.s.data['events']=[dict(id='event',pet='pet',title='Control veterinario',detail='Peso registrado: 4.5 kg',kind='Control',date='2026-11-15 09:30')]
        self.s.data['events'] += [dict(id='e'+str(i),pet='pet',title='Registro '+str(i),detail='',kind='Síntoma',date='2026-11-16 11:00') for i in range(4)]
        assert self.s.save()
        self.out=Path('previews/story');self.out.mkdir(parents=True,exist_ok=True)
        self.states=iter((width,page) for width in (390,320) for page in ('Perfil','Rutina','Salud','Historial'))
        Clock.schedule_once(self.next,.3)

    def next(self,_):
        item=next(self.states,None)
        if item is None:
            self.s.preview_tag();Clock.schedule_once(self.turn,.3);return
        self.width,self.page=item;Window.size=(self.width,844 if self.width==390 else 640)
        self.modal=None
        if self.page=='Perfil':
            self.detail_patch=patch.object(self.s,'task_detail');self.details=self.detail_patch.start()
            self.s.profile(self.pet)
        elif self.page=='Historial':self.s.history()
        else:self.s.show(self.page)
        Clock.schedule_once(self.capture,.3)

    def capture(self,_):
        target=next((w for w in Window.children if hasattr(w,'dismiss')),self.root)
        for w in target.walk():
            if isinstance(w,ViewText) and w.wrap:assert w.height+1>=w.texture_size[1],w.text
        target.export_to_png(str(self.out/f'{self.page}-{self.width}.png'))
        if self.page=='Salud':
            events=[w for w in reversed(self.s.content.children) if w.__class__.__name__=='StoryEvent']
            assert [w.context['title'] for w in events]==['Paseo','Registro 3','Registro 2']
            assert events[1].context['date'].startswith('Síntoma\n')
        if self.page=='Perfil':
            next(w for w in target.walk() if isinstance(w,ViewAction) and w.text=='Ver cuidado').dispatch('on_release')
            self.details.assert_called_once()
            assert self.details.call_args.args[0]['id']==('0' if self.width==390 else '1')
            self.detail_patch.stop()
        if self.page=='Rutina' and self.width==390:
            self.s.toggle_routine('0')
            labels=[w.text for w in self.s.content.walk() if isinstance(w,ViewText)]
            assert '1 de 2 cuidados de hoy' in labels and 'Completados' in labels
            assert self.s.data['routines'][0]['due_at']=='2026-11-17 08:00'
        if hasattr(target,'dismiss'):target.dismiss(animation=False)
        Clock.schedule_once(self.next,.1)

    def turn(self,_):
        self.modal=next(w for w in Window.children if hasattr(w,'dismiss'))
        self.frame=next(w for w in self.modal.walk() if w.__class__.__name__=='TagLarge')
        self.frame.dispatch('on_release');self.frame.dispatch('on_release')
        self.turn_checks=0
        Clock.schedule_once(self.turned,.4)

    def turned(self,_):
        if self.frame.turning:
            self.turn_checks+=1;assert self.turn_checks<15;Clock.schedule_once(self.turned,.1);return
        assert self.frame.turn_scale==1 and Path(self.frame.ids.image.source).name.endswith('reverso.png')
        self.s.motion_enabled=lambda:False
        self.frame.dispatch('on_release')
        assert Path(self.frame.ids.image.source).name=='chapa-web-3d.png'
        self.s.motion_enabled=lambda:True
        self.frame.dispatch('on_release');self.modal.dismiss(animation=False)
        Clock.schedule_once(self.cancelled,.4)

    def cancelled(self,_):
        assert not self.frame.turning and self.frame.turn_scale==1
        assert Path(self.frame.ids.image.source).name=='chapa-web-3d.png'
        for p in self.patches:p.stop()
        self.stop();self.tmp.cleanup()
        print('PASS: pet hub actions, real daily progress/recurrence, health timeline, 8 captures and tag turn/reduced motion/cancellation')


if __name__=='__main__':Check().run()
