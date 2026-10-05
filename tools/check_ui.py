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
from screens.views import ViewAction, ViewSpinner, ViewTextInput, load_views, view


class CheckUI(MiMascotaApp):
    def build(self):
        self.temporary = TemporaryDirectory()
        from unittest.mock import patch
        with patch("screens.home.DATA_FILE", Path(self.temporary.name) / "state.json"):
            manager = super().build()
        self.screen = manager.get_screen("home")
        return manager

    def on_start(self):
        from unittest.mock import patch, PropertyMock
        with patch("screens.home.platform", "android"), patch.object(type(self), "user_data_dir", new_callable=PropertyMock) as data_dir:
            data_dir.return_value = self.temporary.name
            mobile = HomeScreen()
            assert mobile.data_file == Path(self.temporary.name) / "petcare.json"
            mobile.reminder_clock.cancel()
        self.pages = iter(["Inicio", "Mascotas", "Rutina", "Salud"])
        self.preview_dir = Path(os.environ.get("MIMASCOTA_PREVIEW_DIR", str(ROOT / "previews")))
        self.preview_dir.mkdir(parents=True, exist_ok=True)
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
        Clock.schedule_once(self.capture, .6)

    def capture(self, _):
        # Un controlador funcional también debe renderizar contenido visible.
        assert self.screen.content.height > 0
        assert self.screen.content.children
        assert self.screen.content.children[-1].opacity > .95
        assert all(child.width > 0 and child.height > 0 for child in self.screen.content.children)
        screenshot = self.preview_dir / f"{self.page}.png"
        self.root.export_to_png(str(screenshot))
        self.assert_visible_pixels(screenshot)
        Clock.schedule_once(self.next_page, .1)

    @staticmethod
    def assert_visible_pixels(path):
        # Un árbol con tamaños correctos puede quedar tapado por un canvas blanco.
        from PIL import Image
        with Image.open(path) as image:
            pixels = image.convert("RGBA")
            visible = sum(1 for r, g, b, a in pixels.getdata()
                          if a > 200 and min(r, g, b) < 200)
            assert visible > pixels.width * pixels.height * .02, f"Vista vacía: {path.name}"

    def capture_small_home(self, _):
        self.root.export_to_png(str(self.preview_dir / "compacta-inicio.png"))
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
        self.check_declarative_views(pet, task)
        s.register_pet()
        # La apertura y su animación comienzan en el primer frame del event loop.
        Clock.schedule_once(lambda _: Clock.schedule_once(self.capture_form, .35), 0)

    @staticmethod
    def dismiss_modals():
        for widget in list(Window.children):
            if hasattr(widget, "dismiss"):
                widget.dismiss(animation=False)

    @staticmethod
    def current_modal():
        return next(widget for widget in Window.children if hasattr(widget, "dismiss"))

    def check_declarative_views(self, pet, task):
        s = self.screen
        # Cargar de nuevo no duplica reglas ni los hijos de las vistas.
        load_views()
        assert len(s.header.children) == 3
        for title in ("Mascotas", "Rutina", "Salud", "Inicio"):
            button = next(b for b in s.nav.children if b.text == title)
            button.dispatch("on_release")
            assert s.active == title and s.subtitle.text == title
        # Las variantes sin assets siguen usando los componentes KV.
        assert len(view("HomeVectorTag").children) == 0
        assert len(view("RoutineVectorBanner").children) == 3
        for open_dialog in (lambda: s.profile(pet), lambda: s.task_detail(task),
                            s.history, s.notifications, s.account,
                            lambda: s.message("Prueba", "Mensaje")):
            open_dialog()
            modal = self.current_modal()
            assert modal.ids.card.children
            self.dismiss_modals()
        accepted = []
        s.confirm("Prueba", "Confirmación", lambda: accepted.append(True))
        modal = self.current_modal()
        button = next(w for w in modal.walk() if isinstance(w, ViewAction) and w.text == "Confirmar")
        button.dispatch("on_release")
        assert accepted == [True]
        self.dismiss_modals()
        s.register_pet()
        modal = self.current_modal()
        species = next(w for w in modal.walk() if isinstance(w, ViewSpinner) and w.text == "Seleccionar especie")
        species.text = "Otro"
        custom = next(w for w in modal.walk() if isinstance(w, ViewTextInput) and w.hint_text == "Ej.: Tortuga")
        assert custom.parent is not None
        species.text = "Gato"
        assert custom.parent.parent is None
        self.dismiss_modals()

    def capture_form(self, _):
        for widget in list(Window.children):
            if hasattr(widget, "dismiss"):
                assert widget.ids.card.width > 0 and widget.ids.card.height > 0
                widget.ids.card.export_to_png(str(self.preview_dir / "formulario.png"))
                widget.dismiss(animation=False)
        Clock.schedule_once(self.next_page, .3)

    def finish(self, _):
        self.root.export_to_png(str(self.preview_dir / "compacta.png"))
        print("PASS: guest, registration, care completion, medical history, persistence, four screens and 320px.")
        self.stop()
        self.temporary.cleanup()


if __name__ == "__main__":
    CheckUI().run()
