"""Flujos funcionales: invitado local, cuidados y acceso opcional a Supabase."""
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import json
import re
from threading import Thread
import uuid

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from pathlib import Path
from screens.widgets import Card, Action, Text, PetAvatar, SpaArt, SpaBanner, TagArt, FloatingTag, SoftSpinner, row, column, PRIMARY, INK, MUTED, MINT, WHITE, LIME
from services.store import LocalStore, normalize, pet_values, complete_task, pending, import_guest, DATE_FORMAT, KINDS
from services.cloud import CloudError
from services.qr import start_trial, trial_expired, write_preview_png, TRIAL_DAYS


class CareFeatures:
    def save(self):
        try:
            self.store.save(self.data)
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.data = deepcopy(self.store.data)
            self.message("No se pudo guardar", str(exc) if isinstance(exc, ValueError) else "Revisa el espacio y los permisos del dispositivo. El cambio no fue guardado.")
            return False

    def home(self):
        tasks = pending(self.data)
        late = pending(self.data, due_only=True)
        self.heading("Siempre cerca.", "Su cuidado diario, en un solo lugar.",
                     "TU ESPACIO" if self.cloud.user else "SIN CUENTA · DATOS LOCALES")
        hero = Card(bg="#103D49", padding=20, spacing=10, radius=28)
        hero_top = row(height=22, spacing=4)
        hero_top.add_widget(Text("01 / TU CHAPA", 10, LIME, bold=True))
        hero_top.add_widget(Text("14 DÍAS", 10, LIME, bold=True, halign="right",
                                 size_hint_x=.35))
        hero.add_widget(hero_top)
        hero_story = row(height=142, spacing=0)
        hero_story.add_widget(Text("Si se pierde,\nque vuelva\ncontigo.", 22, WHITE,
                                   bold=True))
        tag_path = Path(__file__).resolve().parents[1] / "assets" / "Placa_Icon.png"
        tag_art = FloatingTag if tag_path.exists() else TagArt
        hero_story.add_widget(tag_art(size_hint_x=None, width=dp(112)))
        hero.add_widget(hero_story)
        hero.add_widget(Text("Su camino de vuelta comienza aquí. Prueba el QR sin crear una cuenta.",
                             12, "#D8EAEC", height=46))
        hero.add_widget(Action("ABRIR MI CHAPA QR", icon="qrcode-scan", bg=LIME, fg="#103D49",
                               height=50, radius=16, callback=self.qr_info))
        self.content.add_widget(hero)
        card = column(adaptive=True, spacing=10)
        card.add_widget(Text("02 / HOY EN UN VISTAZO", 11, PRIMARY, bold=True, height=24))
        counts = row(height=86, spacing=6)
        for number, label in ((len(self.data["pets"]), "Mascotas"),
                              (len(tasks), "Cuidados\npendientes"),
                              (len(late), "Cuidados\natrasados")):
            metric = column(spacing=0)
            metric.add_widget(Text(str(number).zfill(2), 29, INK, bold=True, height=43))
            metric.add_widget(Text(label, 11, MUTED, height=38))
            counts.add_widget(metric)
        card.add_widget(counts)
        if not self.data["pets"]:
            card.add_widget(Text("Empieza por registrar a tu mascota.\nNo necesitas crear una cuenta.", 13, MUTED, height=44))
            card.add_widget(Action("Registrar mi primera mascota", icon="paw", callback=self.register_pet))
        else:
            card.add_widget(Action("Ver mis mascotas", icon="paw", callback=partial(self.show, "Mascotas")))
        self.content.add_widget(card)
        if tasks:
            task = tasks[0]
            card = Card(padding=16, spacing=10)
            card.add_widget(Text("PRÓXIMO CUIDADO", 11, PRIMARY, height=20))
            card.add_widget(self.detail_row(task["icon"] if task["icon"] in ("paw", "walk", "creation", "bathtub-outline") else "calendar-clock",
                                           task["title"], f'{self.pet_name(task["pet"])} · {task["time"]}'))
            card.add_widget(Action("Ver detalle y completar", icon="check-circle-outline", callback=partial(self.task_detail, task)))
            self.content.add_widget(card)
        else:
            self.content.add_widget(self.link_card("calendar-clock", "Todo a tu ritmo", "Agrega tu próximo cuidado en Rutina", "Rutina"))
        self.content.add_widget(self.link_card("bathtub-outline", "Rutina & Mimos", "Paseos, higiene y recordatorios", "Rutina"))
        self.content.add_widget(self.link_card("heart-pulse", "Salud y bienestar", "Vacunas, tratamientos e historial", "Salud"))
        card = Card(bg=MINT, padding=16, spacing=10)
        card.add_widget(Text("Tus datos, a tu manera", 16, PRIMARY, bold=True, height=25))
        card.add_widget(Text("Puedes usar los cuidados sin conexión.\nCon una cuenta también puedes guardar una copia en la nube.", 12, MUTED, height=51))
        card.add_widget(Action("Mi cuenta y copias de seguridad", icon="cloud-outline", callback=self.account))
        self.content.add_widget(card)

    def pet_name(self, pet_id):
        return next((p["name"] for p in self.data["pets"] if p["id"] == pet_id), "General")

    def chip_text(self, pet):
        if pet["chip"]:
            return pet["chip"]
        return {"Sí": "Número pendiente", "No": "No"}.get(pet.get("chip_status"), "Sin registrar")

    def weight_text(self, pet):
        return f'{pet["weight"]} kg' if pet["weight"] != "—" else "Sin registrar"

    def pets(self):
        self.heading("Mis Compañeros", f'{len(self.data["pets"])} mascotas en este espacio')
        self.content.add_widget(Action("Registrar mascota", icon="plus", callback=self.register_pet))
        if not self.data["pets"]:
            self.content.add_widget(Text("Aquí verás sus perfiles y datos de cuidado.", 13, MUTED, height=60))
        for pet in self.data["pets"]:
            card = Card(padding=16, spacing=10, accent=True)
            top = row(height=76, spacing=14)
            top.add_widget(PetAvatar(kind=pet["kind"], size_hint_x=None, width=dp(74)))
            copy = column(spacing=4)
            copy.add_widget(Text(pet["name"], 21, INK, bold=True, height=30, shorten=True))
            copy.add_widget(Text(f'{pet["breed"]} · {pet["age"]}', 12, MUTED, height=30, shorten=True))
            top.add_widget(copy)
            card.add_widget(top)
            card.add_widget(Text(f'Peso: {self.weight_text(pet)}   ·   Chip: {self.chip_text(pet)}', 12, PRIMARY, height=30, shorten=True))
            card.add_widget(Action("Abrir QR de " + pet["name"], icon="qrcode-scan", bg=MINT, fg=PRIMARY,
                                   callback=partial(self.qr_info, pet)))
            card.add_widget(Action("Ver perfil y editar", icon="arrow-right", bg=MINT, fg=PRIMARY, callback=partial(self.profile, pet)))
            self.content.add_widget(card)
        card = Card(padding=16, spacing=10)
        card.add_widget(self.detail_row("qrcode-scan", "Chapa digital QR", "Escanea una prueba sin crear cuenta"))
        card.add_widget(Action("Abrir mi chapa de prueba", icon="qrcode-scan", callback=self.qr_info))
        self.content.add_widget(card)

    def register_pet(self, *_, pet=None):
        species = ("Perro", "Gato", "Conejo", "Ave", "Pez", "Reptil", "Hámster", "Otro")
        known_kind = pet.get("kind", "") if pet else ""
        selected_kind = known_kind if known_kind in species[:-1] else ("Otro" if known_kind else "Seleccionar especie")
        old_chip = pet.get("chip", "") if pet else ""
        chip_status = pet.get("chip_status", "Sí" if old_chip else "No sé") if pet else "No sé"
        old_age = pet.get("age", "") if pet else ""
        fields = [
            ("name", "Nombre *", pet.get("name", "") if pet else ""),
            ("kind", "Especie *", selected_kind),
            ("custom_kind", "¿Qué especie? *", known_kind if selected_kind == "Otro" else ""),
            ("breed", "Raza (si la conoces)", pet.get("breed", "") if pet else ""),
            ("age", "Edad (ej.: 3 años)", "" if old_age == "Sin registrar" else old_age),
            ("weight", "Peso en kg (opcional)", pet.get("weight", "").replace("—", "") if pet else ""),
            ("chip_status", "¿Tiene microchip?", chip_status),
            ("chip", "Número de microchip (si lo tienes)", old_chip),
        ]
        def submit(values):
            if values["kind"] == "Seleccionar especie":
                raise ValueError("Selecciona la especie de tu mascota.")
            if values["kind"] == "Otro":
                values["kind"] = values["custom_kind"].strip()
                if not values["kind"]:
                    raise ValueError("Escribe la especie de tu mascota.")
            clean = pet_values(values)
            if pet:
                pet.update(clean)
            else:
                self.data["pets"].append(dict(clean, id=uuid.uuid4().hex))
                self.selected_pet = self.data["pets"][-1]["id"]
        self.form("Editar mascota" if pet else "Nueva mascota", fields, submit,
                  choices={"kind": ("Seleccionar especie",) + species,
                           "chip_status": ("No sé", "Sí", "No")},
                  visible_when={"custom_kind": ("kind", "Otro"), "chip": ("chip_status", "Sí")},
                  hints={"name": "Ej.: Luna", "custom_kind": "Ej.: Tortuga", "age": "Ej.: 3 años",
                         "weight": "Ej.: 4,2", "chip": "Número de la cartilla"},
                  input_types={"weight": "number", "chip": "number"})

    def profile(self, pet, *_):
        modal, card = self.dialog(pet["name"], 510)
        card.add_widget(PetAvatar(kind=pet["kind"], size_hint_y=None, height=dp(95)))
        card.add_widget(Text(f'{pet["breed"]} · {pet["age"]}\nPeso: {self.weight_text(pet)}\nMicrochip: {self.chip_text(pet)}', 14, INK))
        def act(callback, *_):
            modal.dismiss()
            callback()
        card.add_widget(Action("Ver expediente", icon="heart-pulse", callback=partial(act, partial(self.select_pet, pet["id"]))))
        card.add_widget(Action("Ver chapa QR", icon="qrcode-scan", bg=MINT, fg=PRIMARY,
                               callback=partial(act, partial(self.qr_info, pet))))
        card.add_widget(Action("Editar perfil", icon="pencil-outline", bg=MINT, fg=PRIMARY, callback=partial(act, partial(self.register_pet, pet=pet))))
        card.add_widget(Action("Eliminar mascota", bg="#FFF0E9", fg="#A44D2E", callback=partial(act, partial(self.delete_pet, pet))))
        modal.open()

    def delete_pet(self, pet):
        def remove():
            self.data["pets"] = [p for p in self.data["pets"] if p["id"] != pet["id"]]
            self.data["qr_trials"].pop(pet["id"], None)
            for key in ("routines", "events"):
                self.data[key] = [item for item in self.data[key] if item.get("pet") != pet["id"]]
            if self.save():
                try:
                    (self.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")).unlink(missing_ok=True)
                except OSError:
                    pass
                self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
                self.show("Mascotas")
        self.confirm("Eliminar mascota", f'Se eliminará {pet["name"]} y sus cuidados e historial de este espacio. Se conserva la copia local anterior (.bak).', remove)

    def routine(self):
        self.heading("Rutina & Mimos", "Cuidados que se adaptan a su día a día")
        banner_path = Path(__file__).resolve().parents[1] / "assets" / "MascotsBanner.png"
        banner = SpaBanner if banner_path.exists() else SpaArt
        self.content.add_widget(banner(size_hint_y=None, height=dp(220)))
        self.content.add_widget(Action("Agregar cuidado o recordatorio", icon="plus", callback=self.add_routine))
        tasks = sorted(self.data["routines"], key=lambda t: (t["done"], t["due_at"] or "9999"))
        self.content.add_widget(Text(f'{len(pending(self.data))} pendientes · {len(tasks)} en total', 13, MUTED, height=24))
        for task in tasks:
            self.content.add_widget(self.task_card(task))
        if not tasks:
            self.content.add_widget(Text("Agrega un paseo, una toma o una cita.\nTe avisaremos aquí mientras la app esté abierta.", 13, MUTED, height=55))

    def task_card(self, task):
        card = Card(padding=14, spacing=8)
        card.add_widget(self.detail_row("check-circle-outline" if task["done"] else "calendar-clock", task["title"], self.pet_name(task["pet"]) + " · " + task["kind"]))
        card.add_widget(Text(("Completado · " if task["done"] else "") + (task["due_at"] or task["time"]), 12, PRIMARY, height=24))
        actions = row(height=44, spacing=8)
        actions.add_widget(Action("Ver detalles", bg=MINT, fg=PRIMARY, callback=partial(self.task_detail, task)))
        if task["kind"] == "Cuidado":
            actions.add_widget(Action("Reabrir" if task["done"] else "Hecho", icon="check",
                                      callback=partial(self.toggle_routine, task["id"])))
        card.add_widget(actions)
        return card

    def add_routine(self, *_, task=None, kind="Cuidado"):
        if not self.data["pets"]:
            self.prompt_register_pet("Registrar cuidados y recordatorios")
            return
        selected = task.get("pet") if task else self.selected_pet
        selected = selected or self.data["pets"][0]["id"]
        pet_options = {f'{i + 1}. {p["name"]}': p["id"] for i, p in enumerate(self.data["pets"])}
        current = next((label for label, pid in pet_options.items() if pid == selected), next(iter(pet_options)))
        default_time = (datetime.now() + timedelta(hours=1)).strftime(DATE_FORMAT)
        def submit(v):
            if not v["title"].strip():
                raise ValueError("Escribe el nombre de la actividad.")
            try:
                date = datetime.strptime(v["due_at"], DATE_FORMAT)
            except ValueError:
                raise ValueError("Usa una fecha válida: AAAA-MM-DD HH:MM.") from None
            item = dict(title=v["title"], detail=v["detail"], pet=pet_options[v["pet"]], kind=v["kind"],
                        due_at=date.strftime(DATE_FORMAT), time=date.strftime(DATE_FORMAT), repeat=v["repeat"], icon="paw")
            if task:
                task.update(item)
            else:
                self.data["routines"].append(dict(item, id=uuid.uuid4().hex, done=False))
        source = task or {}
        fields = [("pet", "Mascota", current), ("kind", "Tipo de cuidado", source.get("kind", kind)),
                  ("title", "Actividad o medicamento *", source.get("title", "")),
                  ("detail", "Detalles / pauta indicada por tu veterinario", source.get("detail", "")),
                  ("due_at", "Fecha y hora local (AAAA-MM-DD HH:MM)", source.get("due_at") or default_time),
                  ("repeat", "Repetición", source.get("repeat", "No"))]
        self.form("Editar cuidado" if task else "Nuevo cuidado", fields, submit,
                  choices={"pet": list(pet_options), "kind": KINDS, "repeat": ("No", "Diaria", "Semanal")},
                  templates=None if task else {
                      "Paseo": {"title": "Paseo", "kind": "Cuidado", "repeat": "Diaria"},
                      "Cepillado": {"title": "Cepillado", "kind": "Cuidado", "repeat": "Diaria"},
                      "Medicación": {"title": "Dar medicamento", "kind": "Medicamento", "repeat": "Diaria"},
                      "Vacuna": {"title": "Vacuna", "kind": "Vacuna", "repeat": "No"},
                      "Desparasitación": {"title": "Desparasitación", "kind": "Desparasitación", "repeat": "No"},
                      "Cita veterinaria": {"title": "Cita veterinaria", "kind": "Cita", "repeat": "No"}},
                  date_shortcuts={"due_at": (("En 1 hora", timedelta(hours=1)),
                                             ("Mañana", timedelta(days=1)),
                                             ("En 7 días", timedelta(days=7)))},
                  hints={"title": "Ej.: Paseo de la tarde", "due_at": "AAAA-MM-DD HH:MM"})

    def task_detail(self, task, *_):
        modal, card = self.dialog("Detalle del cuidado", 530)
        card.add_widget(Text(task["title"], 20, INK, bold=True, height=48))
        card.add_widget(Text(f'{self.pet_name(task["pet"])} · {task["kind"]}\n{task["time"]}\nRepetición: {task["repeat"]}', 13, PRIMARY, height=65))
        details = Text(task["detail"] or "Sin detalles adicionales", 13, MUTED)
        details.bind(width=lambda instance, width: setattr(instance, "text_size", (width, None)),
                     texture_size=lambda instance, size: setattr(instance, "height", size[1] + dp(12)))
        details.size_hint_y = None
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(details)
        card.add_widget(scroll)
        def act(callback, *_):
            modal.dismiss()
            callback()
        card.add_widget(Action("Volver a pendiente" if task["done"] else "Marcar como realizado", icon="check", callback=partial(act, partial(self.toggle_routine, task["id"]))))
        card.add_widget(Action("Editar / reprogramar", bg=MINT, fg=PRIMARY, callback=partial(act, partial(self.add_routine, task=task))))
        def remove():
            self.data["routines"].remove(task)
            if self.save():
                self.show(self.active)
        card.add_widget(Action("Eliminar cuidado", bg="#FFF0E9", fg="#A44D2E", callback=partial(act, lambda: self.confirm("Eliminar cuidado", "El cuidado se eliminará. Sus registros previos en el historial se conservan.", remove))))
        modal.open()

    def toggle_routine(self, task_id, *_):
        task = next(r for r in self.data["routines"] if r["id"] == task_id)
        complete_task(self.data, task)
        if self.save():
            self.show(self.active)

    def health(self):
        self.heading("Salud y Bienestar", "Expediente y cuidados de cada mascota")
        if not self.data["pets"]:
            self.content.add_widget(Text("Registra tu mascota para crear su expediente.", 13, MUTED, height=55))
            self.content.add_widget(Action("Registrar mascota", icon="plus", callback=self.register_pet))
            return
        if self.selected_pet not in [p["id"] for p in self.data["pets"]]:
            self.selected_pet = self.data["pets"][0]["id"]
        options = {f'{i + 1}. {p["name"]}': p["id"] for i, p in enumerate(self.data["pets"])}
        selector = SoftSpinner(text=next(label for label, pid in options.items() if pid == self.selected_pet),
                               values=list(options), size_hint_y=None, height=dp(44))
        selector.bind(text=lambda _, label: self.select_pet(options[label]))
        self.content.add_widget(selector)
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        card = Card(padding=16, spacing=8, accent=True)
        card.add_widget(Text(self.pet_name(self.selected_pet), 21, INK, bold=True, height=30))
        card.add_widget(Text(f'{len(events)} eventos en el historial\nSin evaluación automática del estado de salud.', 12, MUTED, height=42))
        self.content.add_widget(card)
        self.content.add_widget(Action("Registrar evento médico", icon="clipboard-plus-outline", callback=self.add_event))
        self.content.add_widget(Action("Consultar historial", icon="history", bg=MINT, fg=PRIMARY, callback=self.history))
        self.content.add_widget(Text("Tratamientos y próximas citas", 18, INK, bold=True, height=30))
        tasks = [r for r in pending(self.data) if r["pet"] == self.selected_pet and r["kind"] != "Cuidado"]
        for task in tasks:
            self.content.add_widget(self.task_card(task))
        if not tasks:
            self.content.add_widget(Text("No hay tratamientos o citas pendientes.", 13, MUTED, height=36))
        self.content.add_widget(Action("Agregar tratamiento, vacuna o cita", icon="plus", callback=partial(self.add_routine, kind="Medicamento")))

    def add_event(self, *_, event=None):
        if not self.selected_pet:
            return
        source = event or {}
        def submit(v):
            if not v["title"]:
                raise ValueError("Escribe un título para el evento.")
            try:
                datetime.strptime(v["date"], DATE_FORMAT)
            except ValueError:
                raise ValueError("Usa una fecha válida: AAAA-MM-DD HH:MM.") from None
            if event:
                event.update(v)
            else:
                self.data["events"].append(dict(v, id=uuid.uuid4().hex, pet=self.selected_pet))
        self.form("Editar evento" if event else "Evento médico", [
            ("kind", "Tipo", source.get("kind", "Control")), ("title", "Título *", source.get("title", "")),
            ("date", "Fecha y hora (AAAA-MM-DD HH:MM)", source.get("date", datetime.now().strftime(DATE_FORMAT))),
            ("detail", "Detalles (opcional)", source.get("detail", ""))], submit,
            choices={"kind": ("Control", "Vacuna", "Medicamento", "Alergia", "Enfermedad", "Síntoma", "Desparasitación", "Cita", "Cuidado")},
            date_shortcuts={"date": (("Ahora", timedelta()),
                                     ("Ayer", timedelta(days=-1)),
                                     ("Hace 7 días", timedelta(days=-7)))},
            hints={"title": "Ej.: Control anual", "date": "AAAA-MM-DD HH:MM"})

    def history(self, *_):
        modal, card = self.dialog("Historial médico", 580)
        modal.size_hint_y = .88
        scroll = ScrollView(do_scroll_x=False)
        entries = column(adaptive=True, spacing=12)
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        if not events:
            entries.add_widget(Text("Todavía no hay eventos registrados.", 14, MUTED, height=70))
        for event in sorted(events, key=lambda e: e.get("date", ""), reverse=True):
            item = Card(bg=MINT, padding=12, spacing=6)
            item.add_widget(Text(event["title"], 17, INK, bold=True, height=32, shorten=True))
            item.add_widget(Text(event.get("date", "Sin fecha") + " · " + event.get("kind", "Evento"), 11, MUTED, height=28))
            body = Text(event["detail"] or "Sin detalles adicionales", 13, INK, height=50)
            body.bind(width=lambda w, width: setattr(w, "text_size", (width, None)),
                      texture_size=lambda w, size: setattr(w, "height", size[1] + dp(10)))
            item.add_widget(body)
            def edit(_, e=event):
                modal.dismiss()
                self.add_event(event=e)
            item.add_widget(Action("Editar evento", bg=WHITE, fg=PRIMARY, callback=edit))
            def delete(_, e=event):
                modal.dismiss()
                def remove():
                    self.data["events"].remove(e)
                    if self.save():
                        self.show(self.active)
                self.confirm("Eliminar evento", "Se eliminará este registro del historial.", remove)
            item.add_widget(Action("Eliminar evento", bg=WHITE, fg=MUTED, callback=delete))
            entries.add_widget(item)
        scroll.add_widget(entries)
        card.add_widget(scroll)
        modal.open()

    def form(self, title, fields, submit, choices=None, password=False, persist=True,
             visible_when=None, hints=None, input_types=None, templates=None, date_shortcuts=None):
        modal, card = self.dialog(title)
        modal.size_hint_y = .88
        scroll = ScrollView(do_scroll_x=False)
        inputs = column(adaptive=True, spacing=10)
        entries = {}
        field_rows = {}
        visible_when = visible_when or {}
        hints = hints or {}
        input_types = input_types or {}
        date_shortcuts = date_shortcuts or {}
        for key, caption, value in fields:
            field_row = column(adaptive=True, spacing=4)
            field_row.add_widget(Text(caption, 12, MUTED, height=25))
            if choices and key in choices:
                entry = SoftSpinner(text=value, values=list(choices[key]), size_hint_y=None, height=dp(44))
            else:
                multiline = key == "detail"
                entry = TextInput(text=value, multiline=multiline, password=password and key == "password",
                                  size_hint_y=None, height=dp(85 if multiline else 44), font_size=dp(14),
                                  padding=[dp(12), dp(10)], background_normal="", background_active="",
                                  background_color=(.94, .97, .98, 1), foreground_color=(.06, .19, .22, 1),
                                  hint_text=hints.get(key, ""), input_type=input_types.get(key, "text"))
            entries[key] = entry
            field_row.add_widget(entry)
            if key in date_shortcuts:
                shortcuts = row(height=36, spacing=6)
                for label, offset in date_shortcuts[key]:
                    def set_date(_, target=entry, delta=offset):
                        target.text = (datetime.now() + delta).strftime(DATE_FORMAT)
                    shortcuts.add_widget(Action(label, bg=MINT, fg=PRIMARY, height=36,
                                                font_size=10, callback=set_date))
                field_row.add_widget(shortcuts)
            field_rows[key] = field_row
        template_row = None
        if templates:
            template_row = column(adaptive=True, spacing=4)
            template_row.add_widget(Text("EMPEZAR CON UNA IDEA · PUEDES CAMBIAR TODO", 10, PRIMARY, height=23))
            template = SoftSpinner(text="Elegir idea rápida", values=list(templates),
                                   size_hint_y=None, height=dp(44))
            def apply_template(_, label):
                for key, value in templates.get(label, {}).items():
                    entries[key].text = value
            template.bind(text=apply_template)
            template_row.add_widget(template)
        def update_visible(*_):
            scroll_position = scroll.scroll_y
            inputs.clear_widgets()
            if template_row is not None:
                inputs.add_widget(template_row)
            for key, _, _ in fields:
                condition = visible_when.get(key)
                if condition is None or entries[condition[0]].text == condition[1]:
                    inputs.add_widget(field_rows[key])
            scroll.scroll_y = scroll_position
        for controlling_key in {condition[0] for condition in visible_when.values()}:
            entries[controlling_key].bind(text=update_visible)
        update_visible()
        scroll.add_widget(inputs)
        card.add_widget(scroll)
        error = Text("", 12, "#AA4625", height=0)
        card.add_widget(error)
        def clear_error(*_):
            error.text = ""
            error.height = 0
        for entry in entries.values():
            entry.bind(text=clear_error)
        def save(*_):
            values = {key: field.text if key == "password" else field.text.strip() for key, field in entries.items()}
            try:
                reason = submit(values)
                if reason:
                    raise ValueError(reason)
                if persist and not self.save():
                    modal.dismiss()
                    self.show(self.active)
                    return
            except (ValueError, KeyError) as exc:
                error.text = str(exc)
                error.height = dp(46)
                return
            modal.dismiss()
            if persist:
                self.show(self.active)
        card.add_widget(Action("Continuar" if not persist else "Guardar", icon="check", callback=save))
        modal.open()

    def prompt_register_pet(self, purpose):
        modal, card = self.dialog("Primero, tu mascota", 330)
        card.add_widget(Text(f"Para {purpose.lower()}, registra una mascota. No necesitas crear una cuenta.",
                             14, MUTED))
        def start(*_):
            modal.dismiss()
            self.register_pet()
        card.add_widget(Action("Registrar mascota", icon="paw", callback=start))
        card.add_widget(Action("Ahora no", bg=MINT, fg=PRIMARY, callback=lambda *_: modal.dismiss()))
        modal.open()

    def confirm(self, title, body, callback):
        modal, card = self.dialog(title, 360)
        card.add_widget(Text(body, 14, MUTED))
        def accept(*_):
            modal.dismiss()
            callback()
        card.add_widget(Action("Confirmar", callback=accept))
        card.add_widget(Action("Cancelar", bg=MINT, fg=PRIMARY, callback=lambda *_: modal.dismiss()))
        modal.open()

    def notifications(self, *_):
        tasks = pending(self.data, due_only=True)
        modal, card = self.dialog("Recordatorios", 510)
        scroll = ScrollView(do_scroll_x=False)
        content = column(adaptive=True, spacing=12)
        content.add_widget(Text("Avisos locales mientras la app está abierta.\nLas notificaciones push aún no están activadas.", 12, MUTED, height=50))
        for task in tasks:
            def open_task(_, t=task):
                modal.dismiss()
                self.task_detail(t)
            content.add_widget(Text(f'{self.pet_name(task["pet"])} · {task["time"]}', 12, MUTED, height=30))
            content.add_widget(Action(task["title"], bg=MINT, fg=PRIMARY, callback=open_task))
        if not tasks:
            content.add_widget(Text("No hay recordatorios vencidos.", 14, INK, height=60))
        scroll.add_widget(content)
        card.add_widget(scroll)
        modal.open()

    def check_reminders(self, *_):
        if self.busy:
            return
        due = pending(self.data, due_only=True)
        fresh = {(t["id"], t["due_at"]) for t in due} - self.notified
        if fresh:
            self.notified.update(fresh)
            self.message("Tienes cuidados pendientes", f"Hay {len(due)} recordatorios vencidos. Abre la campana para revisarlos.")

    def qr_info(self, pet=None, *_):
        if not self.data["pets"]:
            self.prompt_register_pet("Crear su chapa QR de prueba")
            return
        if not isinstance(pet, dict):
            pet = next((p for p in self.data["pets"] if p["id"] == self.selected_pet), self.data["pets"][0])
        self.selected_pet = pet["id"]
        trials = self.data["qr_trials"]
        is_new = pet["id"] not in trials
        trial = start_trial(trials, pet["id"])
        if is_new and not self.save():
            return
        modal, card = self.dialog("Chapa de " + pet["name"], 690)
        modal.size_hint_y = .92
        scroll = ScrollView(do_scroll_x=False)
        body = column(adaptive=True, spacing=13)
        body.size_hint_x = None
        scroll.bind(width=body.setter("width"))
        body.add_widget(Text("02 / TU CHAPA DIGITAL", 11, PRIMARY, bold=True, height=24))
        if trial_expired(trial):
            try:
                (self.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")).unlink(missing_ok=True)
            except OSError:
                pass
            body.add_widget(Text("La prueba terminó", 22, INK, bold=True, height=36))
            body.add_widget(Text("El QR de prueba ya no se muestra en la app. Para una caducidad real al escanear, hace falta publicar la ficha mediante Supabase.",
                                 13, MUTED, height=84))
        else:
            expires = datetime.fromisoformat(trial["expires_at"])
            body.add_widget(Text("Pruébala con otra cámara", 21, INK, bold=True, height=36))
            body.add_widget(Text("QR LOCAL · " + str(TRIAL_DAYS) + " DÍAS DESDE SU PRIMERA APERTURA", 10, PRIMARY,
                                 bold=True, height=25))
            qr_path = self.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")
            try:
                write_preview_png(pet, trial, qr_path)
            except (OSError, ValueError):
                modal.dismiss()
                self.message("No se pudo crear el QR", "Revisa el almacenamiento disponible en este dispositivo.")
                return
            qr_frame = Card(bg=WHITE, padding=8, radius=20)
            qr_frame.add_widget(Image(source=str(qr_path), size_hint_y=None, height=dp(240)))
            body.add_widget(qr_frame)
            body.add_widget(Text("Válido en esta app hasta " + expires.strftime("%d/%m/%Y") + ". Escanéalo con la cámara de otro móvil.",
                                 12, INK, height=43))
            body.add_widget(Text("Este QR de prueba muestra solo nombre y especie. No publica una web ni comparte tus datos de contacto. Una foto del código seguirá siendo legible tras el plazo.",
                                 12, MUTED, height=80))
            body.add_widget(Text("PNG: " + str(qr_path), 10, MUTED, height=47))
        assets = Path(__file__).resolve().parents[1] / "assets"
        plate_path = assets / "placa_preview.png"
        front_path = assets / "PlacaReal_Front.png"
        back_path = assets / "PlacaReal_Back.png"
        plate = Card(bg=MINT, padding=14, spacing=8, radius=20)
        plate.add_widget(Text("PRÓXIMAMENTE · PLACA FÍSICA", 11, PRIMARY, bold=True, height=25))
        if front_path.exists() and back_path.exists():
            for title, path in (("Frente · nombre de la mascota", front_path),
                                ("Reverso · QR ilustrativo", back_path)):
                plate.add_widget(Text(title, 12, INK, bold=True, height=24))
                plate.add_widget(Image(source=str(path), fit_mode="contain",
                                       size_hint_y=None, height=dp(205)))
        elif plate_path.exists():
            plate.add_widget(Image(source=str(plate_path), size_hint_y=None, height=dp(180)))
        else:
            plate.add_widget(Text("Una placa con su nombre y un QR permanente para volver a casa.",
                                  14, INK, height=56))
        plate.add_widget(Text("Vista referencial: el QR del mockup no funciona. Cada placa real necesitará un código propio. Compra y envío aún no disponibles.",
                              11, MUTED, height=70))
        body.add_widget(plate)
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()
        def layout_qr(_):
            card.do_layout()
            body.width = scroll.width
            body.do_layout()
            if not trial_expired(trial):
                qr_frame.do_layout()
            plate.do_layout()
            scroll.update_from_scroll()
            body.pos = (scroll.x, scroll.top - body.height)
            body.do_layout()
            if not trial_expired(trial):
                qr_frame.do_layout()
            plate.do_layout()
        Clock.schedule_once(layout_qr, 0)

    def account(self, *_):
        user = self.cloud.user
        modal, card = self.dialog("Mi cuenta" if user else "Continúa a tu ritmo", 600)
        modal.size_hint_y = .90
        scroll = ScrollView(do_scroll_x=False)
        body = column(adaptive=True, spacing=12)
        body.add_widget(Text(user.get("email", "Cuenta") if user else "Estás usando Mi Mascota como invitado.", 16, PRIMARY, height=50))
        body.add_widget(Text("Mascotas, salud y rutinas funcionan sin cuenta.\nLa cuenta permite guardar y recuperar tu copia privada en la nube.", 13, MUTED, height=80))
        def action(label, callback):
            def run(*_):
                modal.dismiss()
                callback()
            body.add_widget(Action(label, callback=run))
        if user:
            action("Guardar copia en la nube", self.upload)
            action("Restaurar copia de la nube", self.download)
            action("Importar datos del invitado", self.import_local)
            action("Cerrar sesión", self.logout)
        else:
            action("Crear cuenta", partial(self.auth_form, True))
            action("Ya tengo cuenta", partial(self.auth_form, False))
        action("Exportar copia local", self.export_backup)
        body.add_widget(Text("Al cerrar sesión vuelves al espacio del invitado.\nLa contraseña y los tokens no se guardan en archivos.", 12, MUTED, height=55))
        action("Volver a Mi Mascota", lambda: None)
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()

    def auth_form(self, signup):
        if not self.cloud.configured:
            self.message("Conexión pendiente", "Puedes seguir usando Mi Mascota sin cuenta. Para activar el registro, configura Supabase con config.example.json y supabase/schema.sql.")
            return
        def submit(v):
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v["email"]):
                raise ValueError("Escribe un correo válido.")
            if len(v["password"]) < (8 if signup else 1):
                raise ValueError("Usa una contraseña de al menos 8 caracteres.")
            self.network(lambda: self.cloud.authenticate(v["email"], v["password"], signup), self.authenticated)
        self.form("Crear cuenta" if signup else "Iniciar sesión", [("email", "Correo electrónico", ""),
                  ("password", "Contraseña", "")], submit, password=True, persist=False)

    def authenticated(self, signed_in):
        if not signed_in:
            self.message("Revisa tu correo", "Si el registro fue aceptado, recibirás un enlace para confirmar tu correo. Después vuelve a Mi Mascota e inicia sesión.")
            return
        user_id = str(uuid.UUID(self.cloud.user["id"]))
        self.switch_store(self.guest_file.parent / "accounts" / (user_id + ".json"))
        self.message("Tu cuenta está lista", "Tus datos de invitado siguen guardados por separado. En Mi cuenta puedes importarlos o restaurar una copia de nube.")

    def switch_store(self, path):
        self.store = LocalStore(path)
        self.data_file = self.store.path
        self.data = deepcopy(self.store.data)
        self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
        self.notified.clear()
        self.show("Inicio")
        if self.store.readonly:
            self.message("Archivo protegido", "No se pudo leer este espacio local. No se sobrescribirá. Revisa el archivo y su copia .bak.")

    def network(self, operation, callback):
        if self.busy:
            return
        self.busy = True
        self.shell.disabled = True
        wait = ModalView(size_hint=(.85, None), height=dp(130), auto_dismiss=False,
                         background_color=(0, 0, 0, 0))
        card = Card(adaptive=False, padding=22)
        card.add_widget(Text("Conectando…\nTus datos locales están seguros.", 15, PRIMARY))
        wait.add_widget(card)
        wait.open()
        def run():
            try:
                result, error = operation(), None
            except CloudError as exc:
                result, error = None, str(exc)
            except Exception:
                result, error = None, "No se pudo completar la operación. Tus datos locales se conservaron."
            def finish(_):
                wait.dismiss()
                self.busy = False
                self.shell.disabled = False
                if error:
                    self.message("No se completó", error)
                else:
                    try:
                        callback(result)
                    except (OSError, ValueError, KeyError, TypeError):
                        self.message("No se completó", "La respuesta o el archivo no son válidos. Tus datos anteriores se conservaron.")
            Clock.schedule_once(finish)
        Thread(target=run, daemon=True).start()

    def require_account(self):
        if self.cloud.user:
            return True
        self.account()
        return False

    def upload(self):
        if not self.require_account():
            return
        snapshot = deepcopy(self.data)
        def done(result):
            self.data["cloud_revision"] = result["revision"]
            if self.save():
                self.message("Copia guardada", "Tu copia privada está en Supabase. Los nuevos cambios seguirán guardándose localmente hasta que vuelvas a guardar una copia.")
        self.network(lambda: self.cloud.upload(snapshot), done)

    def download(self):
        if not self.require_account():
            return
        def received(result):
            if not result:
                self.message("Sin copia todavía", "Esta cuenta no tiene datos guardados en la nube.")
                return
            incoming = normalize(result["data"])
            incoming["cloud_revision"] = result["revision"]
            def restore():
                try:
                    self.backup_file("antes-de-restaurar")
                    self.store.save(incoming)
                except (OSError, ValueError):
                    self.message("No se pudo restaurar", "La copia de seguridad o el guardado fallaron. No se reemplazó tu estado local.")
                    return
                self.switch_store(self.data_file)
            self.confirm("Restaurar copia", f'La copia contiene {len(incoming["pets"])} mascotas. Reemplazará los datos de esta cuenta en el dispositivo. Antes se guardará un respaldo local.', restore)
        self.network(self.cloud.download, received)

    def import_local(self):
        if not self.require_account():
            return
        guest = LocalStore(self.guest_file)
        if guest.readonly:
            self.message("No se pudo importar", "El archivo del invitado no se puede leer. Se conservó sin cambios.")
            return
        def transfer():
            self.data = import_guest(self.data, guest.data)
            if self.save():
                self.show("Inicio")
                self.message("Importación local lista", "Los registros se copiaron a tu cuenta en este dispositivo. Para subirlos, elige Guardar copia en la nube. El original del invitado se conserva.")
        self.confirm("Importar invitado", "Copia las mascotas, rutinas e historial de este dispositivo a tu cuenta. Hazlo sólo si esos datos son tuyos. Los registros ya importados no se duplican.", transfer)

    def backup_file(self, prefix="copia"):
        folder = self.data_file.parent / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{prefix}-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def export_backup(self):
        try:
            path = self.backup_file()
            self.message("Copia exportada", "Archivo guardado en:\n" + str(path))
        except OSError:
            self.message("No se pudo exportar", "Revisa el espacio y los permisos de escritura.")

    def logout(self):
        def leave():
            try:
                self.cloud.logout()
                return True
            except CloudError:
                return False
        def done(revoked):
            self.switch_store(self.guest_file)
            if not revoked:
                self.message("Sesión local cerrada", "Se borraron los tokens de esta sesión, pero no se pudo revocar la sesión remota por falta de conexión.")
        self.network(leave, done)
