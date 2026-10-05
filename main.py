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

    def build(self):

        # Tema general
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        self.title = "Mi Mascota"

        load_views()
        manager = Builder.load_file(str(Path(__file__).resolve().parent / 'main.kv'))
        # La pantalla aplica primero sus reglas KV y el fondo de KivyMD.
        # Después su controlador añade el contenido, por encima del fondo.
        manager.add_widget(HomeScreen(name="home"))
        return manager

    def on_stop(self):
        if self.root and hasattr(self.root, "get_screen"):
            self.root.get_screen("home").reminder_clock.cancel()


if __name__ == "__main__":
    MiMascotaApp().run()
    
