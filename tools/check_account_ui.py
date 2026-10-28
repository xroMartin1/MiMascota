import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
os.environ['KIVY_NO_ARGS']='1'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import MiMascotaApp
from screens.home import HomeScreen
from screens.date_field import DateField
from screens.views import ViewAction
from kivy.clock import Clock
from kivy.core.window import Window


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        with patch('screens.home.DATA_FILE',Path(self.temp.name)/'guest.json'):
            return super().build()

    def on_start(self):
        self.screen = self.root.get_screen('home')
        self.screen.cloud.configured if False else None
        self.screen.cloud.request = Mock(side_effect=Exception('No real network in UI test'))
        self.screen.cloud.restore_session = Mock(return_value=False)
        self.screen.check_google_provider = lambda *_: None
        self.screen._backup_clock.cancel()
        self.screen.mobile.configured if False else None
        Clock.schedule_once(self.date_form,.5)

    def date_form(self,_):
        self.modal, entries = self.screen.form('Un cuidado', [('due_at','Fecha y hora','2030-10-09 18:30')], lambda _:None)
        self.field = entries['due_at']
        assert isinstance(self.field,DateField)
        assert self.field.date_button.text == '9 oct 2030'
        assert self.field.time_button.text == '18:30'
        Clock.schedule_once(self.capture_form,.4)
        Clock.schedule_once(self.calendar,.6)

    def capture_form(self,_):
        output=Path(__file__).resolve().parents[1]/'previews'/'account'
        output.mkdir(parents=True,exist_ok=True)
        self.modal.export_to_png(str(output/'date-form.png'))

    def calendar(self,_):
        self.field.pick_date()
        from kivymd.uix.pickers import MDDatePicker
        self.picker=next(w for w in Window.children if isinstance(w,MDDatePicker))
        Clock.schedule_once(self.select_date,.7)

    def select_date(self,_):
        from datetime import date
        self.picker.dispatch('on_save',date(2030,10,12),[])
        self.picker.dismiss()
        assert self.field.text == '2030-10-12 18:30'
        self.field.pick_time()
        from kivymd.uix.pickers import MDTimePicker
        self.picker=next(w for w in Window.children if isinstance(w,MDTimePicker))
        Clock.schedule_once(self.select_time,.5)

    def select_time(self,_):
        from datetime import time
        self.picker.dispatch('on_save',time(9,15))
        assert self.field.text == '2030-10-12 09:15'
        self.modal.dismiss()
        self.screen.cloud.configured if False else None
        self.screen.auth_form(False)
        Clock.schedule_once(self.login,.4)

    def login(self,_):
        buttons=[w for root in Window.children for w in root.walk() if isinstance(w,ViewAction)]
        assert any(w.text=='Olvidé mi contraseña' for w in buttons)
        button=next(w for w in buttons if w.text=='Olvidé mi contraseña')
        button.dispatch('on_release')
        Clock.schedule_once(self.recovery,.4)

    def recovery(self,_):
        buttons=[w for root in Window.children for w in root.walk() if isinstance(w,ViewAction)]
        assert any(w.text=='Enviar enlace' for w in buttons)
        print('PASS: calendar, time picker, storage format and recovery navigation')
        self.stop()

Check().run()
