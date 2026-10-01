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
from pathlib import Path
from screens.views import view
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
        hero = view('HomeHero')
        hero_story = view('HomeHeroStory')
        tag_path = Path(__file__).resolve().parents[1] / "assets" / "Placa_Icon.png"
        hero_story.add_widget(view('HomeFloatingTag' if tag_path.exists() else 'HomeVectorTag'))
        hero.add_widget(hero_story)
        hero.add_widget(view('HomeQrDescription'))
        hero.add_widget(view('HomeOpenQr', callback=self.qr_info))
        self.content.add_widget(hero)
        card = view('HomeOverview')
        counts = view('HomeCounts')
        for number, label in ((len(self.data["pets"]), "Mascotas"),
                              (len(tasks), "Cuidados\npendientes"),
                              (len(late), "Cuidados\natrasados")):
            metric = view('HomeMetric', number=str(number).zfill(2), label=label)
            counts.add_widget(metric)
        card.add_widget(counts)
        if not self.data["pets"]:
            card.add_widget(view('HomeEmptyPets'))
            card.add_widget(view('HomeRegisterPet', callback=self.register_pet))
        else:
            card.add_widget(view('HomeViewPets', callback=partial(self.show, 'Mascotas')))
        self.content.add_widget(card)
        if tasks:
            task = tasks[0]
            card = view('HomeNextCare')
            card.add_widget(self.detail_row(task["icon"] if task["icon"] in ("paw", "walk", "creation", "bathtub-outline") else "calendar-clock",
                                           task["title"], f'{self.pet_name(task["pet"])} · {task["time"]}'))
            card.add_widget(view('HomeCareDetails', callback=partial(self.task_detail, task)))
            self.content.add_widget(card)
        else:
            self.content.add_widget(self.link_card("calendar-clock", "Todo a tu ritmo", "Agrega tu próximo cuidado en Rutina", "Rutina"))
        self.content.add_widget(self.link_card("bathtub-outline", "Rutina & Mimos", "Paseos, higiene y recordatorios", "Rutina"))
        self.content.add_widget(self.link_card("heart-pulse", "Salud y bienestar", "Vacunas, tratamientos e historial", "Salud"))
        card = view('HomeAccount', callback=self.account)
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
        self.content.add_widget(view('PetsRegister', callback=self.register_pet))
        if not self.data["pets"]:
            self.content.add_widget(view('PetsEmpty'))
        for pet in self.data["pets"]:
            card = view(
                'PetCard',
                kind=pet['kind'],
                name=pet['name'],
                summary=f"{pet['breed']} · {pet['age']}",
                details=f'Peso: {self.weight_text(pet)}   ·   Chip: {self.chip_text(pet)}',
                qr_label='Abrir QR de ' + pet['name'],
                open_qr=partial(self.qr_info, pet),
                open_profile=partial(self.profile, pet),
            )
            self.content.add_widget(card)
        card = view('PetsQrCard')
        card.add_widget(self.detail_row("qrcode-scan", "Chapa digital QR", "Escanea una prueba sin crear cuenta"))
        card.add_widget(view('PetsOpenQr', callback=self.qr_info))
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
        card.add_widget(view('ProfileAvatar', kind=pet['kind']))
        card.add_widget(view(
            'ProfileSummary',
            text=f"{pet['breed']} · {pet['age']}\nPeso: {self.weight_text(pet)}\nMicrochip: {self.chip_text(pet)}",
        ))
        def act(callback, *_):
            modal.dismiss()
            callback()
        card.add_widget(view('ProfileHealth', callback=partial(act, partial(self.select_pet, pet['id']))))
        card.add_widget(view('ProfileQr', callback=partial(act, partial(self.qr_info, pet))))
        card.add_widget(view('ProfileEdit', callback=partial(act, partial(self.register_pet, pet=pet))))
        card.add_widget(view('ProfileDelete', callback=partial(act, partial(self.delete_pet, pet))))
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
        self.content.add_widget(view('RoutineImageBanner' if banner_path.exists() else 'RoutineVectorBanner'))
        self.content.add_widget(view('RoutineAdd', callback=self.add_routine))
        tasks = sorted(self.data["routines"], key=lambda t: (t["done"], t["due_at"] or "9999"))
        self.content.add_widget(view(
            'RoutineCount',
            text=f'{len(pending(self.data))} pendientes · {len(tasks)} en total',
        ))
        for task in tasks:
            self.content.add_widget(self.task_card(task))
        if not tasks:
            self.content.add_widget(view('RoutineEmpty'))

    def task_card(self, task):
        card = view('CareTaskCard')
        card.add_widget(self.detail_row("check-circle-outline" if task["done"] else "calendar-clock", task["title"], self.pet_name(task["pet"]) + " · " + task["kind"]))
        actions = view('CareTaskActions', callback=partial(self.task_detail, task))
        card.add_widget(view(
            'CareTaskDate',
            text=('Completado · ' if task['done'] else '') + (task['due_at'] or task['time']),
        ))
        if task["kind"] == "Cuidado":
            actions.add_widget(view(
                'CareTaskToggle',
                text='Reabrir' if task['done'] else 'Hecho',
                callback=partial(self.toggle_routine, task['id']),
            ))
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
        details = view('TaskDetailDetails', text=task['detail'] or 'Sin detalles adicionales')
        card.add_widget(view('TaskTitle', text=task['title']))
        card.add_widget(view(
            'TaskSummary',
            text=f"{self.pet_name(task['pet'])} · {task['kind']}\n{task['time']}\nRepetición: {task['repeat']}",
        ))
        scroll = view('TaskDetailScroll')
        scroll.add_widget(details)
        card.add_widget(scroll)
        def act(callback, *_):
            modal.dismiss()
            callback()
        card.add_widget(view(
            'TaskComplete',
            text='Volver a pendiente' if task['done'] else 'Marcar como realizado',
            callback=partial(act, partial(self.toggle_routine, task['id'])),
        ))
        card.add_widget(view('TaskEdit', callback=partial(act, partial(self.add_routine, task=task))))
        def remove():
            self.data["routines"].remove(task)
            if self.save():
                self.show(self.active)
        card.add_widget(view(
            'TaskDelete',
            callback=partial(act, lambda: self.confirm('Eliminar cuidado', 'El cuidado se eliminará. Sus registros previos en el historial se conservan.', remove)),
        ))
        modal.open()

    def toggle_routine(self, task_id, *_):
        task = next(r for r in self.data["routines"] if r["id"] == task_id)
        complete_task(self.data, task)
        if self.save():
            self.show(self.active)

    def health(self):
        self.heading("Salud y Bienestar", "Expediente y cuidados de cada mascota")
        if not self.data["pets"]:
            self.content.add_widget(view('HealthEmptyPets'))
            self.content.add_widget(view('HealthRegisterPet', callback=self.register_pet))
            return
        if self.selected_pet not in [p["id"] for p in self.data["pets"]]:
            self.selected_pet = self.data["pets"][0]["id"]
        options = {f'{i + 1}. {p["name"]}': p["id"] for i, p in enumerate(self.data["pets"])}
        selector = view(
            'HealthSelector',
            text=next((label for label, pid in options.items() if pid == self.selected_pet)),
            values=list(options),
        )
        selector.bind(text=lambda _, label: self.select_pet(options[label]))
        self.content.add_widget(selector)
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        card = view(
            'HealthSummary',
            name=self.pet_name(self.selected_pet),
            summary=f'{len(events)} eventos en el historial\nSin evaluación automática del estado de salud.',
        )
        self.content.add_widget(card)
        self.content.add_widget(view('HealthAddEvent', callback=self.add_event))
        self.content.add_widget(view('HealthHistory', callback=self.history))
        self.content.add_widget(view('HealthTreatmentTitle'))
        tasks = [r for r in pending(self.data) if r["pet"] == self.selected_pet and r["kind"] != "Cuidado"]
        for task in tasks:
            self.content.add_widget(self.task_card(task))
        if not tasks:
            self.content.add_widget(view('HealthEmptyTasks'))
        self.content.add_widget(view(
            'HealthAddTreatment',
            callback=partial(self.add_routine, kind='Medicamento'),
        ))

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
        scroll = view('HistoryScroll')
        entries = view('HistoryEntries')
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        if not events:
            entries.add_widget(view('HistoryEmpty'))
        for event in sorted(events, key=lambda e: e.get("date", ""), reverse=True):
            item = view(
                'HistoryItem',
                title=event['title'],
                date=event.get('date', 'Sin fecha') + ' · ' + event.get('kind', 'Evento'),
            )
            body = view('HistoryBody', text=event['detail'] or 'Sin detalles adicionales')
            item.add_widget(body)
            def edit(_, e=event):
                modal.dismiss()
                self.add_event(event=e)
            item.add_widget(view('HistoryEdit', callback=edit))
            def delete(_, e=event):
                modal.dismiss()
                def remove():
                    self.data["events"].remove(e)
                    if self.save():
                        self.show(self.active)
                self.confirm("Eliminar evento", "Se eliminará este registro del historial.", remove)
            item.add_widget(view('HistoryDelete', callback=delete))
            entries.add_widget(item)
        scroll.add_widget(entries)
        card.add_widget(scroll)
        modal.open()

    def form(self, title, fields, submit, choices=None, password=False, persist=True,
             visible_when=None, hints=None, input_types=None, templates=None, date_shortcuts=None):
        modal, card = self.dialog(title)
        modal.size_hint_y = .88
        scroll = view('FormScroll')
        inputs = view('FormInputs')
        entries = {}
        field_rows = {}
        visible_when = visible_when or {}
        hints = hints or {}
        input_types = input_types or {}
        date_shortcuts = date_shortcuts or {}
        for key, caption, value in fields:
            field_row = view('FormFieldRow', text=caption)
            if choices and key in choices:
                entry = view('FormChoice', text=value, values=list(choices[key]))
            else:
                multiline = key == "detail"
                entry = view(
                    'FormTextInput',
                    text=value,
                    multiline=multiline,
                    password=password and key == 'password',
                    hint_text=hints.get(key, ''),
                    input_type=input_types.get(key, 'text'),
                )
            entries[key] = entry
            field_row.add_widget(entry)
            if key in date_shortcuts:
                shortcuts = view('FormShortcuts')
                for label, offset in date_shortcuts[key]:
                    def set_date(_, target=entry, delta=offset):
                        target.text = (datetime.now() + delta).strftime(DATE_FORMAT)
                    shortcuts.add_widget(view('FormDateShortcut', text=label, callback=set_date))
                field_row.add_widget(shortcuts)
            field_rows[key] = field_row
        template_row = None
        if templates:
            template_row = view('FormTemplateRow')
            template = view('FormTemplate', values=list(templates))
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
        error = view('FormError')
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
        card.add_widget(view('FormSubmit', text='Continuar' if not persist else 'Guardar', callback=save))
        modal.open()

    def prompt_register_pet(self, purpose):
        modal, card = self.dialog("Primero, tu mascota", 330)
        card.add_widget(view(
            'RegistrationPrompt',
            text=f'Para {purpose.lower()}, registra una mascota. No necesitas crear una cuenta.',
        ))
        def start(*_):
            modal.dismiss()
            self.register_pet()
        card.add_widget(view('RegistrationStart', callback=start))
        card.add_widget(view('RegistrationCancel', callback=lambda *_: modal.dismiss()))
        modal.open()

    def confirm(self, title, body, callback):
        modal, card = self.dialog(title, 360)
        card.add_widget(view('ConfirmationBody', text=body))
        def accept(*_):
            modal.dismiss()
            callback()
        card.add_widget(view('ConfirmationAccept', callback=accept))
        card.add_widget(view('ConfirmationCancel', callback=lambda *_: modal.dismiss()))
        modal.open()

    def notifications(self, *_):
        tasks = pending(self.data, due_only=True)
        modal, card = self.dialog("Recordatorios", 510)
        scroll = view('NotificationsScroll')
        content = view('NotificationsContent')
        for task in tasks:
            def open_task(_, t=task):
                modal.dismiss()
                self.task_detail(t)
            content.add_widget(view('NotificationDate', text=f"{self.pet_name(task['pet'])} · {task['time']}"))
            content.add_widget(view('NotificationOpenTask', text=task['title'], callback=open_task))
        if not tasks:
            content.add_widget(view('NotificationsEmpty'))
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
        scroll = view('QrInfoScroll')
        body = view('QrInfoBody')
        body.add_widget(view('QrTitle'))
        if trial_expired(trial):
            try:
                (self.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")).unlink(missing_ok=True)
            except OSError:
                pass
            body.add_widget(view('QrExpiredTitle'))
            body.add_widget(view('QrExpiredDescription'))
        else:
            expires = datetime.fromisoformat(trial["expires_at"])
            body.add_widget(view('QrActiveTitle'))
            body.add_widget(view(
                'QrTrialPeriod',
                text='QR LOCAL · ' + str(TRIAL_DAYS) + ' DÍAS DESDE SU PRIMERA APERTURA',
            ))
            qr_path = self.data_file.parent / "qr" / ("prueba-" + pet["id"] + ".png")
            try:
                write_preview_png(pet, trial, qr_path)
            except (OSError, ValueError):
                modal.dismiss()
                self.message("No se pudo crear el QR", "Revisa el almacenamiento disponible en este dispositivo.")
                return
            qr_frame = view('QrInfoQrFrame', source=str(qr_path))
            body.add_widget(qr_frame)
            body.add_widget(view(
                'QrExpiry',
                text='Válido en esta app hasta ' + expires.strftime('%d/%m/%Y') + '. Escanéalo con la cámara de otro móvil.',
            ))
            body.add_widget(view('QrPrivacy'))
            body.add_widget(view('QrFilePath', text='PNG: ' + str(qr_path)))
        assets = Path(__file__).resolve().parents[1] / "assets"
        plate_path = assets / "placa_preview.png"
        front_path = assets / "PlacaReal_Front.png"
        back_path = assets / "PlacaReal_Back.png"
        plate = view('QrInfoPlate')
        if front_path.exists() and back_path.exists():
            for title, path in (("Frente · nombre de la mascota", front_path),
                                ("Reverso · QR ilustrativo", back_path)):
                plate.add_widget(view('PlateSideTitle', text=title))
                plate.add_widget(view('PlateSideImage', source=str(path)))
        elif plate_path.exists():
            plate.add_widget(view('PlatePreview', source=str(plate_path)))
        else:
            plate.add_widget(view('PlateFallback'))
        plate.add_widget(view('PlateDisclaimer'))
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
        scroll = view('AccountScroll')
        body = view(
            'AccountBody',
            text=user.get('email', 'Cuenta') if user else 'Estás usando Mi Mascota como invitado.',
        )
        def action(label, callback):
            def run(*_):
                modal.dismiss()
                callback()
            body.add_widget(view('AccountAction', text=label, callback=run))
        if user:
            action("Guardar copia en la nube", self.upload)
            action("Restaurar copia de la nube", self.download)
            action("Importar datos del invitado", self.import_local)
            action("Cerrar sesión", self.logout)
        else:
            action("Crear cuenta", partial(self.auth_form, True))
            action("Ya tengo cuenta", partial(self.auth_form, False))
        action("Exportar copia local", self.export_backup)
        body.add_widget(view('AccountSessionNote'))
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
        wait = view('NetworkWait')
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
