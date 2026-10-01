"""Dibujo vectorial y animaciones; las jerarquías visuales están en widgets.kv."""
from pathlib import Path
import math
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line, Triangle, Rectangle, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as rgba

PRIMARY = "#286F83"
INK = "#193C47"
LIME = "#DAEFA0"
WHITE = "#FFFFFF"


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
    kind = StringProperty("Perro")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw, kind=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            size = min(self.width, self.height)
            pet_face(self.center_x - size / 2, self.center_y - size / 2, size, self.kind.casefold() == "gato")


class TagArt(Widget):
    """Una chapa editorial decorativa; el QR que se escanea se genera por separado."""
    def __init__(self, **kwargs):
        self.phase = 0.0
        self._motion = None
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)

    def on_parent(self, _instance, parent):
        if self._motion is not None:
            self._motion.cancel()
            self._motion = None
        if parent is not None:
            self._motion = Clock.schedule_interval(self._tick, 1 / 12)

    def _tick(self, delta):
        self.phase += delta
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        x, y, w, h = self.x, self.y, self.width, self.height
        s = min(w / dp(125), h / dp(140))
        cx, cy = x + w * .52, y + h * .50
        tw, th = dp(86) * s, dp(108) * s
        left, bottom = cx - tw / 2, cy - th / 2
        with self.canvas:
            Color(.16, .44, .52, .22)
            Line(ellipse=(x + dp(8) * s, y + dp(5) * s,
                          w - dp(16) * s, h - dp(10) * s), width=1)
            for px, py, size in ((.13, .72, 4), (.88, .28, 5), (.78, .86, 3)):
                Color(.16, .44, .52, .46)
                Ellipse(pos=(x + w * px, y + h * py), size=(dp(size) * s, dp(size) * s))
            PushMatrix()
            Rotate(angle=-9 + math.sin(self.phase * 1.4) * 2.2, origin=(cx, cy))
            Color(0, 0, 0, .18)
            RoundedRectangle(pos=(left + dp(5) * s, bottom - dp(5) * s),
                             size=(tw, th), radius=[dp(17) * s])
            Color(*rgba(LIME))
            RoundedRectangle(pos=(left, bottom), size=(tw, th), radius=[dp(17) * s])
            Color(*rgba(INK))
            Ellipse(pos=(cx - dp(6) * s, bottom + th - dp(19) * s),
                    size=(dp(12) * s, dp(12) * s))
            qx, qy = left + dp(18) * s, bottom + dp(26) * s
            unit = dp(6) * s
            Line(rectangle=(qx, qy + unit * 4, unit * 3, unit * 3), width=1.6)
            Rectangle(pos=(qx + unit, qy + unit * 5), size=(unit, unit))
            for gx, gy in ((4, 6), (5, 6), (6, 6), (4, 4), (6, 4), (0, 2), (2, 2),
                           (4, 2), (6, 2), (0, 0), (2, 0), (5, 0), (6, 0)):
                Rectangle(pos=(qx + gx * unit, qy + gy * unit), size=(unit * .7, unit * .7))
            Color(*rgba(PRIMARY))
            RoundedRectangle(pos=(left + dp(18) * s, bottom + dp(12) * s),
                             size=(tw - dp(36) * s, dp(3) * s), radius=[dp(2) * s])
            PopMatrix()


class FloatingTag(FloatLayout):
    """Mueve suavemente la ilustración 2D sin volver a generar su textura."""
    source = StringProperty(str(Path(__file__).resolve().parents[1] / "assets" / "Placa_Icon.png"))

    def __init__(self, **kwargs):
        self.phase = 0.0
        self._motion = None
        super().__init__(**kwargs)
        self.image = self.ids.image
        self.bind(pos=self._place, size=self._place)

    def on_parent(self, _instance, parent):
        if self._motion is not None:
            self._motion.cancel()
            self._motion = None
        if parent is not None:
            self._motion = Clock.schedule_interval(self._tick, 1 / 20)

    def _tick(self, delta):
        self.phase += delta
        self._place()

    def _place(self, *_):
        self.image.center = (self.center_x, self.center_y + math.sin(self.phase * 1.7) * dp(3))


class SpaArt(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag = self.ids.tag
        self.title = self.ids.title
        self.caption = self.ids.caption
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


class SpaBanner(FloatLayout):
    """Ilustración con textos declarativos definidos en widgets.kv."""
    source = StringProperty(str(Path(__file__).resolve().parents[1] / "assets" / "MascotsBanner.png"))
