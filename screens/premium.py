"""Personalized product preview and cancellable Premium accents."""
import math
from pathlib import Path

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as rgba

from screens.views import ViewAction, ViewColumn, interface_motion


class PersonalTag(Widget):
    name = StringProperty('Tu mascota')
    source = StringProperty('assets/chapa-personalizable.png')

    def __init__(self, **kwargs):
        self._image = None
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw, name=self.draw, source=self.draw)
        self.draw()

    def draw(self, *_):
        side = min(self.width, self.height)
        x, y = self.center_x - side / 2, self.center_y - side / 2
        path = Path(self.source)
        if path.is_file() and (not self._image or self._image.filename != str(path)):
            self._image = CoreImage(str(path))
        text = ' '.join(self.name.split()) or 'Tu mascota'
        label = CoreLabel(text=text, font_size=max(dp(10), side * .105), bold=True)
        label.refresh()
        # Fit the actual rendered Unicode name, including very long unbroken names.
        self._name_texture = label.texture
        scale = min(1, side * .58 / max(1, label.texture.width))
        self._name_size = label.texture.width * scale, label.texture.height * scale
        self.canvas.clear()
        with self.canvas:
            if path.is_file() and self._image:
                Color(1, 1, 1, 1)
                image_width = side * self._image.width / self._image.height
                Rectangle(pos=(self.center_x-image_width/2, y), size=(image_width, side), texture=self._image.texture)
            else:
                Color(*rgba('#2A5058'))
                Ellipse(pos=(x + side * .17, y + side * .1), size=(side * .66, side * .66))
                Color(*rgba('#B5D2CE'))
                Ellipse(pos=(x + side * .19, y + side * .13), size=(side * .62, side * .62))
                Color(*rgba('#E6F1E5'))
                Ellipse(pos=(x + side * .22, y + side * .17), size=(side * .56, side * .56))
                Color(*rgba('#7CA69E'))
                Line(circle=(self.center_x, y + side * .79, side * .065), width=max(1, side * .012))
            Color(*rgba('#24494D'))
            Rectangle(texture=label.texture, size=self._name_size,
                      pos=(self.center_x-self._name_size[0]/2, y+side*(.34 if path.is_file() else .43)-self._name_size[1]/2))


class PremiumAccountButton(ViewAction):
    premium = BooleanProperty(False)
    motion_active = BooleanProperty(True)

    def __init__(self, **kwargs):
        self._ring_event = None
        self._phase = 0
        super().__init__(**kwargs)
        self.bind(pos=self._draw_ring, size=self._draw_ring, premium=self.refresh_motion,
                  motion_active=self.refresh_motion)

    def on_parent(self, instance, parent):
        super().on_parent(instance, parent)
        self.refresh_motion()

    def refresh_motion(self, *_):
        if self._ring_event:
            self._ring_event.cancel()
            self._ring_event = None
        if self.parent is not None and self.premium and self.motion_active and interface_motion():
            self._ring_event = Clock.schedule_interval(self._tick, 1/30)
        self._draw_ring()

    def _tick(self, dt):
        if not interface_motion():
            self.refresh_motion()
            return
        self._phase = (self._phase + dt / 12) % 1
        self._draw_ring()

    def _draw_ring(self, *_):
        if not hasattr(self, '_ring_canvas'):
            from kivy.graphics import InstructionGroup
            self._ring_canvas = InstructionGroup()
            self.canvas.after.add(self._ring_canvas)
        self._ring_canvas.clear()
        if not self.premium:
            return
        radius = min(dp(self.radius), self.width/2-1, self.height/2-1)
        palette = [rgba(c) for c in ('#85BDB8', '#D3E6A8', '#C9BDE6', '#85BDB8')]
        points = []
        for cx, cy, start in ((self.right-radius-1,self.top-radius-1,0),
                              (self.x+radius+1,self.top-radius-1,90),
                              (self.x+radius+1,self.y+radius+1,180),
                              (self.right-radius-1,self.y+radius+1,270)):
            for step in range(17):
                a = math.radians(start+step*90/16)
                points.append((cx+radius*math.cos(a), cy+radius*math.sin(a)))
        points.append(points[0])
        for i, (a, b) in enumerate(zip(points, points[1:])):
            offset = ((i/(len(points)-1)+self._phase)%1)*3
            index = int(offset)
            mix = offset-index
            color = [palette[index][j]*(1-mix)+palette[index+1][j]*mix for j in range(3)]
            self._ring_canvas.add(Color(*color, .85))
            self._ring_canvas.add(Line(points=(*a,*b), width=dp(1.15)))


class PremiumWelcome(ViewColumn):
    phase = NumericProperty(1)
    motion_active = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(phase=self._draw_paws, pos=self._draw_paws, size=self._draw_paws,
                  motion_active=self._motion_changed)

    def on_parent(self, _, parent):
        if parent is None:
            Animation.cancel_all(self, 'phase')
            self.phase = 1
        else:
            self.present()

    def _motion_changed(self, *_):
        if not self.motion_active:
            Animation.cancel_all(self, 'phase')
            self.phase = 1

    def present(self):
        Animation.cancel_all(self, 'phase')
        self.phase = 1
        if self.parent is not None and self.motion_active and interface_motion():
            self.phase = 0
            Animation(phase=1, duration=1.4, t='out_sine').start(self)

    def _draw_paws(self, *_):
        if not hasattr(self, '_paw_canvas'):
            from kivy.graphics import InstructionGroup
            self._paw_canvas = InstructionGroup()
            self.canvas.after.add(self._paw_canvas)
        self._paw_canvas.clear()
        if not self.motion_active or self.phase >= 1:
            return
        if not interface_motion():
            Animation.cancel_all(self, 'phase')
            self.phase = 1
            return
        for index, horizontal in enumerate((.15,.82,.27,.72)):
            x = self.x+self.width*horizontal
            y = self.top-dp(85+index*18)+self.phase*dp(26)
            self._paw_canvas.add(Color(*rgba(('#85BDB8','#C9BDE6')[index%2])[:3], (1-self.phase)*.7))
            for px, py, w, h in ((0,0,8,7),(-3,7,4,5),(2,10,4,5),(7,8,4,5)):
                self._paw_canvas.add(Ellipse(pos=(x+dp(px),y+dp(py)),size=(dp(w),dp(h))))


def register():
    for cls in (PersonalTag, PremiumAccountButton, PremiumWelcome):
        Factory.register(cls.__name__, cls=cls)
