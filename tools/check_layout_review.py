from pathlib import Path
import sys, os
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from main import MiMascotaApp
from services.store import pet_values, DATE_FORMAT
from screens.views import ViewText
from kivy.clock import Clock
from kivy.core.window import Window

class Review(MiMascotaApp):
    def build(self):
        self.temp=TemporaryDirectory()
        with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'):
            manager=super().build()
        self.s=manager.get_screen('home')
        self.s.cloud=Mock(user=None,configured=False,config={})
        self.s.mobile=Mock(configured=False)
        self.output=Path(os.getenv('AUDIT_OUTPUT', str(ROOT/'previews'/'layout-review')));self.output.mkdir(parents=True,exist_ok=True)
        return manager
    def on_start(self):
        s=self.s
        pet=pet_values({'name':'Luna María de la familia Rodríguez','kind':'Gato','breed':'Siamesa','age':'2 años','weight':'4.2'})
        pet['id']='fixture'
        s.data['pets']=[pet];s.selected_pet=pet['id']
        s.data['routines']=[dict(id='care',title='Paseo y cepillado después de comer',detail='Un paseo tranquilo de 30 minutos.',pet='fixture',kind='Cuidado',repeat='Diaria',done=False,icon='paw',due_at=(datetime.now()+timedelta(hours=1)).strftime(DATE_FORMAT),time='Hoy por la tarde')]
        self.pages=iter([(width,page) for width in (390,320) for page in ('Inicio','Mascotas','Rutina','Salud','Cuenta','Chapa')])
        Clock.schedule_once(self.next,.3)
    def next(self,_):
        item=next(self.pages,None)
        if item is None:
            self.stop();self.temp.cleanup();print('PASS: six pages, long pet/task names, 390/320px and heading layout');return
        width,page=item
        Window.size=(width,844 if width==390 else 640)
        self.page=page;self.width=width
        self.s.show(page)
        Clock.schedule_once(self.capture,.45)
    def capture(self,_):
        self.root.export_to_png(str(self.output/(self.page+'-'+str(self.width)+'.png')))
        for widget in self.s.content.walk():
            if isinstance(widget,ViewText) and widget.text and widget.width>0:
                assert widget.width<=Window.width, (self.page,widget.text)
                if widget.wrap:
                    assert widget.height + 1 >= widget.texture_size[1], ('clipped text',self.page,widget.text)
            if widget.__class__.__name__ == 'HeadingBox':
                children=sorted(widget.children,key=lambda w:w.y)
                for lower,upper in zip(children,children[1:]):
                    assert lower.top <= upper.y + 1, ('heading overlap',self.page)
        Clock.schedule_once(self.next,.05)

if __name__=='__main__':Review().run()
