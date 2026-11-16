import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kivy.clock import Clock
from main import MiMascotaApp

class TestApp(MiMascotaApp):
    def on_start(self):
        Clock.schedule_once(self.check, 0.5)

    def check(self, dt):
        s = self.root.screens[0]
        color_instr = s.canvas.children[4]
        print('FINAL Color rgba:', color_instr.rgba)
        print('Canvas order:')
        for i, c in enumerate(s.canvas.children):
            print(f'  {i}: {c}')
        self.stop()

if __name__ == '__main__':
    TestApp().run()
