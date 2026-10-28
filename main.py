from pathlib import Path

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.utils import get_color_from_hex, platform

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from screens.home import HomeScreen
from screens.views import load_views


# Simulación de pantalla de teléfono sólo en escritorio.
if platform not in ("android", "ios"):
    Window.size = (390, 844)
    Window.minimum_width = 320
    Window.minimum_height = 560
Window.softinput_mode = "below_target"

# Fondo general de la aplicación
Window.clearcolor = get_color_from_hex("#FFFFFF")


class MiMascotaApp(MDApp):

    def configure_system_bars(self):
        if platform == 'android':
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            autoclass('org.mimascota.SystemBars').install(activity)

    def on_start(self):
        self.configure_system_bars()
        Window.bind(on_keyboard=self.back_navigation)

    def back_navigation(self, window, key, *_):
        if key != 27 or not self.root:
            return False
        if any(hasattr(child, 'dismiss') for child in Window.children):
            return False
        screen = self.root.get_screen('home')
        if screen.active == 'Conversación':
            screen.open_qr_inbox()
            return True
        if screen.active == 'Cuidado compartido':
            screen.open_care_sharing()
            return True
        if screen.active == 'Compartidos':
            screen.show('Cuenta')
            return True
        if screen.active in ('Avisos', 'Cuenta', 'Chapa'):
            screen.show('Inicio')
            return True
        return False

    def on_pause(self):
        if self.root:
            self.root.get_screen("home").cloud.retry_session_cache()
        return True

    def on_resume(self):
        self.configure_system_bars()
        from kivy.clock import Clock
        Clock.schedule_once(self.root.get_screen("home").retry_reminders, .5)
        Clock.schedule_once(self.root.get_screen("home").retry_backup, 1)
        Clock.schedule_once(self.root.get_screen("home").refresh_care_tip, 1.2)
        Clock.schedule_once(self.root.get_screen("home").check_google_provider, 1)

    def build(self):

        # Tema general
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        self.title = "Mi Mascota"
        self.icon = str(Path(__file__).resolve().parent / 'assets/brand/icono-app.png')
        if platform not in ('android', 'ios'):
            Window.set_icon(self.icon)

        load_views()
        manager = Builder.load_file(str(Path(__file__).resolve().parent / 'main.kv'))
        # La pantalla aplica primero sus reglas KV y el fondo de KivyMD.
        # Después su controlador añade el contenido, por encima del fondo.
        manager.add_widget(HomeScreen(name="home"))
        return manager

    def on_stop(self):
        if self.root and hasattr(self.root, "get_screen"):
            self.root.get_screen("home").reminder_clock.cancel()
            self.root.get_screen("home").push_sync_clock.cancel()
            self.root.get_screen("home")._backup_clock.cancel()
            self.root.get_screen("home").cloud.retry_session_cache()
            self.root.get_screen('home')._qr_poll.cancel()
            self.root.get_screen('home')._notice_timer.cancel()
            Window.unbind(on_keyboard=self.back_navigation)


if __name__ == "__main__":
    MiMascotaApp().run()
