"""Componentes visuales compartidos; ilustraciones vectoriales dibujadas en Kivy."""
from pathlib import Path
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line, Triangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as rgba
from kivymd import fonts_path
from kivymd.icon_definitions import md_icons

PRIMARY = "#00594D"
INK = "#172D29"
MUTED = "#70827C"
MINT = "#EAF5EF"
PEACH = "#FFF0E9"
WHITE = "#FFFFFF"


def column(adaptive=False, spacing=8, padding=0, **kwargs):
    box = BoxLayout(orientation="vertical", spacing=dp(spacing),
                    padding=[dp(x) for x in padding] if isinstance(padding, (list, tuple)) else dp(padding), **kwargs)
    if adaptive:
        box.size_hint_y = None
        box.bind(minimum_height=box.setter("height"))
    return box


def row(height=40, spacing=8, **kwargs):
    return BoxLayout(size_hint_y=None, height=dp(height), spacing=dp(spacing), **kwargs)


class Text(Label):
    def __init__(self, text="", font_size=14, color=INK, height=None, **kwargs):
        super().__init__(text=text, font_size=sp(font_size), color=rgba(color),
                         halign=kwargs.pop("halign", "left"), valign="middle", **kwargs)
        if height is not None:
            self.size_hint_y = None
            self.height = dp(height)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        self.shorten_from = "right"


class Icon(Text):
    def __init__(self, name, color=PRIMARY, size=22, width=28, **kwargs):
        super().__init__(md_icons[name], size, color, halign="center", font_name=str(Path(fonts_path) / "materialdesignicons-webfont.ttf"), **kwargs)
        self.size_hint_x = None
        self.width = dp(width)


class Card(BoxLayout):
    def __init__(self, bg=WHITE, radius=23, padding=18, spacing=10, adaptive=True, accent=False, **kwargs):
        super().__init__(orientation=kwargs.pop("orientation", "vertical"),
                         padding=padding if isinstance(padding, (list, tuple)) else dp(padding), spacing=dp(spacing), **kwargs)
        self.radius_value = dp(radius)
        self.accent = accent
        with self.canvas.before:
            # Una sombra apenas perceptible mantiene la superficie ligera.
            Color(0.05, .22, .16, .025)
            self.shadow = RoundedRectangle(radius=[self.radius_value])
            self.fill = Color(*rgba(bg))
            self.shape = RoundedRectangle(radius=[self.radius_value])
            if accent:
                Color(*rgba(PRIMARY))
                self.rule = RoundedRectangle(radius=[dp(2)])
        self.bind(pos=self._draw, size=self._draw)
        if adaptive:
            self.size_hint_y = None
            self.bind(minimum_height=self.setter("height"))

    def _draw(self, *_):
        self.shape.pos, self.shape.size = self.pos, self.size
        self.shadow.pos = (self.x, self.y - dp(3))
        self.shadow.size = self.size
        if self.accent:
            self.rule.pos = (self.x + dp(13), self.top - dp(3))
            self.rule.size = (max(0, self.width - dp(26)), dp(3))


class Action(ButtonBehavior, Card):
    def __init__(self, text="", icon=None, callback=None, bg=PRIMARY, fg=WHITE,
                 width=None, height=44, radius=10, vertical=False, font_size=12, **kwargs):
        super().__init__(bg=bg, radius=radius, padding=[dp(4 if vertical else 9), dp(5)], spacing=4,
                         adaptive=False, orientation="vertical" if vertical else "horizontal",
                         size_hint_y=None, height=dp(height), **kwargs)
        if vertical:
            self.size_hint_y = 1
        if width is not None:
            self.size_hint_x, self.width = None, dp(width)
        if icon:
            glyph = Icon(icon, color=fg, size=22 if vertical or not text else 18, width=22)
            if vertical or not text:
                glyph.size_hint_x = 1
            self.add_widget(glyph)
        if text:
            self.add_widget(Text(text, font_size, fg, halign="center", bold=not vertical, shorten=True))
        if callback:
            self.bind(on_release=callback)
        self.bind(state=lambda *_: setattr(self, "opacity", .68 if self.state == "down" else 1))


def pill(text, icon=None, warm=False):
    box = Card(bg=PEACH if warm else MINT, radius=14, orientation="horizontal",
               padding=[dp(10), dp(4)], spacing=5, adaptive=False, size_hint_y=None, height=dp(27))
    if icon:
        box.add_widget(Icon(icon, color="#A44D2E" if warm else PRIMARY, size=13, width=14))
    box.add_widget(Text(text, 10, "#A44D2E" if warm else PRIMARY, shorten=True))
    return box


def icon_tile(icon, size=44, bg=MINT):
    tile = Card(bg=bg, radius=13, adaptive=False, padding=0, size_hint=(None, None), width=dp(size), height=dp(size), pos_hint={"center_y": .5})
    glyph = Icon(icon, size=23, color="#A44D2E" if bg == PEACH else PRIMARY)
    glyph.size_hint_x = 1
    tile.add_widget(glyph)
    return tile


def pet_face(x, y, size, cat=False):
    """Dibuja un avatar sin archivos externos, usando coordenadas normalizadas."""
    def circle(cx, cy, w, h, color):
        Color(*rgba(color))
        Ellipse(pos=(x + cx * size, y + cy * size), size=(w * size, h * size))
    circle(0, 0, 1, 1, "#DDF5EA")
    circle(.08, .08, .84, .84, "#EDEAFF" if cat else "#FFF0D7")
    if cat:
        Color(*rgba("#B4ABDA"))
        Triangle(points=[x+.21*size,y+.50*size,x+.19*size,y+.85*size,x+.46*size,y+.65*size])
        Triangle(points=[x+.54*size,y+.65*size,x+.81*size,y+.85*size,x+.79*size,y+.50*size])
    else:
        circle(.16, .30, .23, .43, "#BC8E51")
        circle(.61, .30, .23, .43, "#BC8E51")
    circle(.27, .23, .46, .49, "#D8D4EE" if cat else "#E8C38B")
    circle(.37, .27, .27, .24, "#F9F5EA")
    for eye in (.36, .57):
        circle(eye, .49, .075, .09, "#427AA5" if cat else "#263B36")
        circle(eye+.012, .53, .024, .026, WHITE)
    circle(.46, .40, .085, .055, "#B47C98" if cat else "#37413A")
    Color(*rgba("#59665B"))
    Line(points=[x+.47*size,y+.34*size,x+.50*size,y+.32*size,x+.55*size,y+.35*size], width=1)
    Color(*rgba("#24A991"))
    Triangle(points=[x+.40*size,y+.23*size,x+.60*size,y+.23*size,x+.50*size,y+.13*size])


class PetAvatar(Widget):
    def __init__(self, kind="Perro", **kwargs):
        self.kind = kind
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            size = min(self.width, self.height)
            pet_face(self.center_x - size / 2, self.center_y - size / 2, size, self.kind.casefold() == "gato")


class SpaArt(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag = Text("DÍA DE SPA & BELLEZA", 10, PRIMARY, bold=True)
        self.title = Text("Momento de consentimiento", 18, WHITE, bold=True)
        self.caption = Text("Un pequeño mimo, una gran felicidad", 11, "#C5ECE0")
        for child in (self.tag, self.title, self.caption):
            self.add_widget(child)
        self.bind(pos=self.draw, size=self.draw)

    def draw(self, *_):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        with self.canvas.before:
            Color(*rgba("#DCEDE5"))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(25)])
            Color(*rgba("#B7DDE1"))
            RoundedRectangle(pos=(x, y+45), size=(w, h*.64), radius=[dp(25)])
            for fx, fy, r in [(.10,.62,10),(.25,.74,6),(.82,.66,12),(.91,.49,6),(.63,.71,7)]:
                Color(.88, 1, 1, .7)
                Ellipse(pos=(x+w*fx, y+h*fy), size=(dp(r), dp(r)))
                Color(.36, .71, .74, .8)
                Line(circle=(x+w*fx+dp(r)/2, y+h*fy+dp(r)/2, dp(r)/2), width=.7)
            for fx, cat in [(.16, False), (.40, True), (.65, False)]:
                pet_face(x+w*fx, y+h*.31, w*.23, cat)
            Color(*rgba("#D6EEEA"))
            for i in range(9):
                Ellipse(pos=(x+i*w/10, y+h*.23), size=(w*.21, h*.18))
            Color(*rgba("#357D6F"))
            RoundedRectangle(pos=(x,y), size=(w, h*.28), radius=[0, 0, dp(25), dp(25)])
            Color(*rgba(WHITE))
            RoundedRectangle(pos=(x+dp(15), y+h-dp(37)), size=(dp(148), dp(23)), radius=[dp(12)])
        self.tag.pos, self.tag.size = (x+dp(23), y+h-dp(36)), (w-dp(40), dp(22))
        self.title.pos, self.title.size = (x+dp(15), y+dp(12)), (w-dp(30), dp(27))
        self.caption.pos, self.caption.size = (x+dp(15), y+dp(39)), (w-dp(30), dp(17))
