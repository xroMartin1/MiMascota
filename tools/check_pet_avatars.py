"""Verify real Kivy avatars pick the matching portrait and retain other species."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION']='1'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.base import EventLoop
from screens.widgets import PetAvatar
from kivy.graphics import Ellipse
EventLoop.ensure_window()
for kind, name in [('Perro','perro.png'),('Gato','gato.png')]:
    avatar=PetAvatar(kind=kind,size=(74,74))
    avatar.draw()
    ellipses=[instruction for instruction in avatar.canvas.children if isinstance(instruction,Ellipse)]
    assert len(ellipses)==1, 'Portrait must replace the old vector drawing'
    assert Path(avatar.portrait_source).name==name
    assert ellipses[0].texture is not None
    avatar.kind='Conejo'
    assert avatar.portrait_source==''
print('PASS: dog/cat textures and other-species fallback')
