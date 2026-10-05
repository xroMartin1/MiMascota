"""Carga de vistas KV y propiedades utilizadas por sus componentes.

Los controladores crean las vistas con ``view(nombre, **datos)``. Los datos
incluyen callbacks; tamaños, colores y jerarquías se definen en los .kv.
"""
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import BooleanProperty, DictProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image

from screens.widgets import FloatingTag, PetAvatar, SpaArt, SpaBanner, TagArt


class ViewColumn(BoxLayout):
    context = DictProperty({})
    adaptive = BooleanProperty(False)

    def on_kv_post(self, base_widget):
        if self.adaptive:
            self.size_hint_y = None
            self.height = self.minimum_height
            self.bind(minimum_height=self.setter('height'))


class ViewRow(BoxLayout):
    context = DictProperty({})


class ViewText(Label):
    context = DictProperty({})
    wrap = BooleanProperty(False)


class ViewCard(ViewColumn):
    bg = StringProperty("#FFFFFF")
    radius = NumericProperty(23)
    accent = BooleanProperty(False)
    adaptive = BooleanProperty(True)


class ViewAction(ButtonBehavior, ViewCard):
    text = StringProperty("")
    icon = StringProperty("")
    fg = StringProperty("#FFFFFF")
    vertical = BooleanProperty(False)
    font_size = NumericProperty(12)
    callback = ObjectProperty(None, allownone=True)

    def on_release(self):
        if self.callback:
            self.callback(self)


class ViewSpinnerOption(SpinnerOption):
    pass


class ViewSpinner(Spinner):
    context = DictProperty({})
    bg = StringProperty("#E7F3F4")
    fg = StringProperty("#286F83")


class ViewPill(ViewCard):
    text = StringProperty("")
    icon = StringProperty("")
    warm = BooleanProperty(False)


class ViewIconTile(ViewCard):
    icon = StringProperty("")
    tile_size = NumericProperty(44)


# Estos widgets tienen comportamiento propio de Kivy o una ilustración Python,
# pero reciben los datos de cada instancia del mismo modo que las otras vistas.
for _base in (ScrollView, ModalView, TextInput, Image, FloatingTag, PetAvatar, SpaArt, SpaBanner, TagArt):
    _name = 'View' + _base.__name__
    _cls = type(_name, (_base,), {'context': DictProperty({})})
    globals()[_name] = _cls
    Factory.register(_name, cls=_cls)


KV_DIR = Path(__file__).resolve().parent
_loaded = False


def load_views():
    """Carga una sola vez, usando rutas independientes del directorio actual."""
    global _loaded
    if _loaded:
        return
    # Las clases de ilustración conservan sus animaciones/dibujo en Python.
    for cls in (FloatingTag, PetAvatar, SpaArt, SpaBanner, TagArt):
        Factory.register(cls.__name__, cls=cls)
    Builder.load_file(str(KV_DIR / "widgets.kv"))
    for filename in ("home.kv", "features.kv"):
        Builder.load_file(str(KV_DIR / filename))
    _loaded = True


def view(template, **context):
    load_views()
    return getattr(Factory, template)(context=context)
