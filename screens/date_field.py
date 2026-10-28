"""Calendar and clock controls with a stable storage format."""
from datetime import datetime
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from screens.views import view
from services.store import DATE_FORMAT


class DateField(BoxLayout):
    text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(48), **kwargs)
        self.date_button = view('FormDateShortcut', text='', callback=lambda *_: self.pick_date())
        self.time_button = view('FormDateShortcut', text='', callback=lambda *_: self.pick_time())
        self.date_button.icon = "calendar-outline"
        self.time_button.icon = "clock-outline"
        for button in (self.date_button, self.time_button):
            button.height = dp(48)
            button.font_size = 14
        self.time_button.size_hint_x = .5
        self.add_widget(self.date_button)
        self.add_widget(self.time_button)
        self.bind(text=self.update_labels)
        self.update_labels()

    def value(self):
        try:
            return datetime.strptime(self.text, DATE_FORMAT)
        except ValueError:
            return datetime.now().replace(second=0, microsecond=0)

    def update_labels(self, *_):
        value = self.value()
        months = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
        self.date_button.text = f'{value.day} {months[value.month-1]} {value.year}'
        self.time_button.text = value.strftime('%H:%M')

    def pick_date(self):
        from kivymd.uix.pickers import MDDatePicker
        value = self.value()
        picker = MDDatePicker(year=value.year, month=value.month, day=value.day)
        def selected(_, date, dates):
            current = self.value()
            self.text = current.replace(year=date.year, month=date.month, day=date.day).strftime(DATE_FORMAT)
        picker.bind(on_save=selected)
        picker.ids.ok_button.text = 'Elegir'
        picker.ids.cancel_button.text = 'Cancelar'
        picker.title = 'ELIGE LA FECHA'
        picker.open()

    def pick_time(self):
        from kivymd.uix.pickers import MDTimePicker
        picker = MDTimePicker()
        picker.set_time(self.value().time())
        def selected(_, time):
            if time:
                self.text = self.value().replace(hour=time.hour, minute=time.minute).strftime(DATE_FORMAT)
            picker.dismiss()
        picker.bind(on_save=selected)
        picker.ids.ok_button.text = 'Elegir'
        picker.ids.cancel_button.text = 'Cancelar'
        picker.open()
