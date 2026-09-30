"""Smoke test real con el event loop de Kivy y capturas de las cuatro pantallas."""
import os
os.environ["KIVY_NO_ARGS"] = "1"
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.home import HomeScreen


class CheckUI(MiMascotaApp):
    def build(self):
        self.temporary = TemporaryDirectory()
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.screen = HomeScreen(data_file=Path(self.temporary.name) / "state.json")
        return self.screen

    def on_start(self):
        from unittest.mock import patch, PropertyMock
        with patch("screens.home.platform", "android"), patch.object(type(self), "user_data_dir", new_callable=PropertyMock) as data_dir:
            data_dir.return_value = self.temporary.name
            mobile = HomeScreen()
            assert mobile.data_file == Path(self.temporary.name) / "petcare.json"
            mobile.reminder_clock.cancel()
        self.pages = iter(["Inicio", "Mascotas", "Rutina", "Salud"])
        (ROOT / "previews").mkdir(exist_ok=True)
        assert self.screen.data["pets"] == []
        self.check_actions()


    def next_page(self, _):
        self.page = next(self.pages, None)
        if self.page is None:
            Window.size = (320, 640)
            self.screen.show("Inicio")
            Clock.schedule_once(self.capture_small_home, .5)
            return
        self.screen.show(self.page)
        Clock.schedule_once(self.capture, .35)

    def capture(self, _):
        self.root.export_to_png(str(ROOT / "previews" / f"{self.page}.png"))
        Clock.schedule_once(self.next_page, .1)

    def capture_small_home(self, _):
        self.root.export_to_png(str(ROOT / "previews" / "compacta-inicio.png"))
        self.screen.show("Mascotas")
        Clock.schedule_once(self.finish, .4)

    def check_actions(self):
        s = self.screen
        captured = []
        original_form = s.form
        s.form = lambda title, fields, submit, **kwargs: captured.append((fields, submit))
        s.register_pet()
        fields, submit = captured.pop()
        values = {key: value for key, _, value in fields}
        values.update(name="Nube", kind="Gato", breed="Común", age="1 año", weight="-1", chip_status="No")
        try:
            submit(values)
            raise AssertionError("Invalid weight accepted")
        except ValueError:
            pass
        values["weight"] = "3.2"
        submit(values)
        assert s.save()
        pet = s.data["pets"][-1]
        s.selected_pet = pet["id"]
        s.qr_info(pet)
        assert pet["id"] in s.data["qr_trials"]
        assert (s.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")).exists()
        for widget in list(Window.children):
            if hasattr(widget, "dismiss"):
                widget.dismiss(animation=False)
        s.add_event()
        _, submit = captured.pop()
        submit(dict(title="Control", detail="Revisión anual", date="2026-09-27 10:00", kind="Control"))
        s.add_routine()
        fields, submit = captured.pop()
        values = {key: value for key, _, value in fields}
        values.update(title="Cepillado", detail="Cepillar con suavidad", due_at="2030-09-27 18:00")
        submit(values)
        task = s.data["routines"][-1]
        s.toggle_routine(task["id"])
        assert task["done"]
        assert any(e.get("task_id") == task["id"] for e in s.data["events"])
        s.toggle_routine(task["id"])
        assert not task["done"]
        assert s.save()
        from services.store import LocalStore
        assert LocalStore(s.data_file).data == s.data
        # Exercise account isolation and explicit guest import through UI handlers.
        from copy import deepcopy
        guest_state = deepcopy(s.data)
        guest_path = s.data_file
        original_confirm = s.confirm
        s.confirm = lambda title, body, callback: callback()
        s.cloud.set_session(dict(access_token="test", refresh_token="test", user={"id": "00000000-0000-0000-0000-000000000001", "email": "test@example.com"}))
        s.authenticated(True)
        assert s.data["pets"] == []
        assert s.data_file != guest_path
        s.import_local()
        assert len(s.data["pets"]) == 1
        s.import_local()
        assert len(s.data["pets"]) == 1
        assert LocalStore(guest_path).data == guest_state
        s.delete_pet(s.data["pets"][0])
        assert s.data["pets"] == [] and s.data["routines"] == [] and s.data["events"] == []
        s.cloud.session = None
        s.switch_store(guest_path)
        assert s.data == guest_state
        s.confirm = original_confirm
        for widget in list(Window.children):
            if hasattr(widget, "dismiss"):
                widget.dismiss(animation=False)
        s.form = original_form
        s.register_pet()
        Clock.schedule_once(self.capture_form, .35)

    def capture_form(self, _):
        for widget in list(Window.children):
            if hasattr(widget, "dismiss"):
                widget.export_to_png(str(ROOT / "previews" / "formulario.png"))
                widget.dismiss(animation=False)
        Clock.schedule_once(self.next_page, .3)

    def finish(self, _):
        self.root.export_to_png(str(ROOT / "previews" / "compacta.png"))
        print("PASS: guest, registration, care completion, medical history, persistence, four screens and 320px.")
        self.stop()
        self.temporary.cleanup()


if __name__ == "__main__":
    CheckUI().run()
