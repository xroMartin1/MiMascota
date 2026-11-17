"""Verify real Kivy avatars pick the matching portrait and retain other species."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.base import EventLoop
from screens.widgets import PetAvatar
from kivy.graphics import Ellipse, Rectangle
EventLoop.ensure_window()
for kind, name in [('Perro','perro.png'),('Gato','gato.png')]:
    avatar=PetAvatar(kind=kind,size=(74,74))
    avatar.draw()
    assert not any(isinstance(instruction,Ellipse) for instruction in avatar.canvas.children), 'Portrait must not have a circular crop'
    rectangles=[instruction for instruction in avatar.canvas.children if isinstance(instruction,Rectangle)]
    assert len(rectangles)==1, 'Portrait must use one transparent texture'
    assert Path(avatar.portrait_source).name==name
    assert rectangles[0].texture is not None
    avatar.kind='Conejo'
    assert avatar.portrait_source==''
    assert avatar.fallback_icon=='rabbit'
    avatar.kind='Reptil'
    assert avatar.fallback_icon=='snake'
print('PASS: dog/cat textures and other-species fallback')
