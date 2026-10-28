"""Flujos funcionales: invitado local, cuidados y acceso opcional a Supabase."""
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import json
import re
import webbrowser
from kivy.utils import platform
from threading import Thread
import uuid

from kivy.clock import Clock
from kivy.metrics import dp
from pathlib import Path
from screens.views import view
from services.store import LocalStore, normalize, pet_values, complete_task, pending, import_guest, DATE_FORMAT, KINDS, care_now
from services.cloud import CloudError
from services.push import PushClient
from services.reminders import zone_label
from services.profile import contact_values, registration_values
from services.qr import start_trial, trial_expired, write_preview_png, TRIAL_DAYS
from screens.public_tag import PublicTagFeatures
from screens.reminders import ReminderFeatures
from screens.date_field import DateField


def readable_date(value, now=None):
    try:
        date = datetime.strptime(value, DATE_FORMAT)
    except (ValueError, TypeError):
        return value
    now = now or datetime.now()
    days = (date.date() - now.date()).days
    if days == 0:
        day = 'Hoy'
    elif days == 1:
        day = 'Mañana'
    else:
        months = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
        day = f'{date.day} {months[date.month-1]}' + (f' {date.year}' if date.year != now.year else '')
    return day + date.strftime(' · %H:%M')


class CareFeatures(ReminderFeatures, PublicTagFeatures):
    def save(self):
        try:
            self.store.save(self.data)
            self.queue_reminders()
            if hasattr(self, "queue_backup"):
                self.queue_backup()
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.data = deepcopy(self.store.data)
            self.message("No se pudo guardar", str(exc) if isinstance(exc, ValueError) else "Revisa el espacio y los permisos del dispositivo. El cambio no fue guardado.")
            return False

    def home(self):
        tasks = pending(self.data)
        late = pending(self.data, due_only=True)
        self.heading("Siempre cerca.", "Su cuidado diario, en un solo lugar.",
                     "TU ESPACIO" if self.cloud.user else "EN ESTE TELÉFONO")
        hero = view('HomeHero')
        hero_story = view('HomeHeroStory')
        tag_path = Path(__file__).resolve().parents[1] / "assets" / "Placa_Icon.png"
        hero_story.add_widget(view('HomeFloatingTag' if tag_path.exists() else 'HomeVectorTag'))
        hero.add_widget(hero_story)
        hero.add_widget(view('HomeQrDescription'))
        hero.add_widget(view('HomeOpenQr', callback=partial(self.show, 'Chapa')))
        self.content.add_widget(hero)
        self.content.add_widget(self.care_tip())
        card = view('HomeOverview')
        counts = view('HomeCounts')
        for number, label in ((len(self.data["pets"]), "Mascotas"),
                              (len(tasks) - len(late), "Cuidados\npendientes"),
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
                                           task["title"], f'{self.pet_name(task["pet"])} · {readable_date(task["due_at"] or task["time"], care_now(self.data))}'))
            card.add_widget(view('HomeCareDetails', callback=partial(self.task_detail, task)))
            self.content.add_widget(card)
        else:
            self.content.add_widget(self.link_card("calendar-clock", "Todo a tu ritmo", "Agrega tu próximo cuidado en Rutina", "Rutina"))
        self.content.add_widget(self.link_card("heart-pulse", "Salud y bienestar", "Vacunas, tratamientos e historial", "Salud"))
        if not self.cloud.user:
            self.content.add_widget(view('HomeAccount', callback=self.account))

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
        shared = ' Al guardarse en tu cuenta, se retirarán sus accesos compartidos e invitaciones.' if self.cloud.user else ''
        self.confirm("Eliminar mascota", f'Se eliminará {pet["name"]} y sus cuidados e historial.' + shared, remove)

    def routine(self):
        self.heading("Sus cuidados", "Paseos, medicamentos y próximas citas")
        banner_path = Path(__file__).resolve().parents[1] / "assets" / "MascotsBanner.png"
        self.content.add_widget(view('RoutineImageBanner' if banner_path.exists() else 'RoutineVectorBanner'))
        self.content.add_widget(view('RoutineAdd', callback=self.add_routine))
        if self.cloud.user and self.mobile.configured:
            status = ('Avisos pendientes de actualizar' if self.data.get('reminder_dirty') else
                      getattr(self, 'reminder_status', '') or ('Avisos automáticos activos' if self.data.get('reminder_settings', {}).get('enabled') else 'Avisos automáticos desactivados'))
            self.content.add_widget(view('UxRow', title='Recordatorios', detail=status, icon='bell-outline', callback=lambda *_: self.reminder_panel()))
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
            text=('Completado · ' if task['done'] else '') + readable_date(task['due_at'] or task['time'], care_now(self.data)),
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
        default_time = (care_now(self.data) + timedelta(hours=1)).strftime(DATE_FORMAT)
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
                  ("due_at", ("Fecha y hora · " + zone_label(self.data["reminder_settings"]["timezone"]) if self.data.get("reminder_settings", {}).get("enabled") else "Fecha y hora"), source.get("due_at") or default_time),
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
        was_done = task['done']
        complete_task(self.data, task)
        if self.save():
            self.show(self.active)
            self.saved_feedback('Cuidado pendiente' if was_done else 'Cuidado realizado')

    def health(self):
        self.heading("Su salud", "Vacunas, tratamientos e historial")
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
            summary=f'{len(events)} registros en el historial\nÚltimas consultas y cuidados de tu mascota.',
            export=lambda *_: self.export_health_report(),
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
            ("date", "Fecha y hora", source.get("date", care_now(self.data).strftime(DATE_FORMAT))),
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
                date=readable_date(event.get('date', 'Sin fecha'), care_now(self.data)) + ' · ' + event.get('kind', 'Evento'),
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
             visible_when=None, hints=None, input_types=None, templates=None, date_shortcuts=None, description=None, submit_text=None):
        modal, card = self.dialog(title)
        modal.size_hint_y = .88
        scroll = view('FormScroll')
        inputs = view('FormInputs')
        intro = view('AccountNote', text=description) if description else None
        entries = {}
        field_rows = {}
        visible_when = visible_when or {}
        hints = hints or {}
        input_types = input_types or {}
        date_shortcuts = date_shortcuts or {}
        for key, caption, value in fields:
            field_row = view('FormFieldRow', text=caption)
            if key in ("due_at", "date"):
                entry = DateField(text=value)
            elif choices and key in choices:
                entry = view('FormChoice', text=value, values=list(choices[key]))
            else:
                multiline = key == "detail"
                entry = view(
                    'FormTextInput',
                    text=value,
                    multiline=multiline,
                    password=password and 'password' in key,
                    hint_text=hints.get(key, ''),
                    input_type=input_types.get(key, 'text'),
                )
            entries[key] = entry
            if password and 'password' in key:
                password_row = view('PasswordRow')
                password_row.add_widget(entry)
                def toggle(button, target=entry):
                    target.password = not target.password
                    button.icon = 'eye-outline' if target.password else 'eye-off-outline'
                password_row.add_widget(view('PasswordEye', callback=toggle))
                field_row.add_widget(password_row)
            else:
                field_row.add_widget(entry)
            if key in date_shortcuts:
                shortcuts = view('FormShortcuts')
                for label, offset in date_shortcuts[key]:
                    def set_date(_, target=entry, delta=offset):
                        target.text = (care_now(self.data) + delta).strftime(DATE_FORMAT)
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
            if intro is not None:
                inputs.add_widget(intro)
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
            values = {key: field.text if "password" in key else field.text.strip() for key, field in entries.items()}
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
                self.saved_feedback('Cambios guardados')
        card.add_widget(view('FormSubmit', text=submit_text or ('Continuar' if not persist else 'Guardar'), callback=save))
        modal.open()
        return modal, entries

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

    def qr_info(self, pet=None, *_, local=False):
        if not self.data["pets"]:
            self.prompt_register_pet("Crear su chapa QR de prueba")
            return
        if not isinstance(pet, dict):
            pet = next((p for p in self.data["pets"] if p["id"] == self.selected_pet), self.data["pets"][0])
        self.selected_pet = pet["id"]
        if self.cloud.user and not local:
            self.open_public_tag(pet)
            return
        trials = self.data["qr_trials"]
        is_new = pet["id"] not in trials
        trial = start_trial(trials, pet["id"])
        if is_new and not self.save():
            return
        modal, card = self.dialog("Chapa de " + pet["name"], 690)
        modal.size_hint_y = .92
        scroll = view('QrInfoScroll')
        body = view('QrInfoBody')
        if not self.cloud.user:
            def web_account(*_):
                modal.dismiss()
                self.account()
            body.add_widget(view('AccountAction', text='Crear chapa web con mi cuenta', callback=web_account))
        body.add_widget(view('QrTitle'))
        contact = pet.get('qr_contact', {})
        has_contact = isinstance(contact, dict) and contact.get('share_phone') is True
        body.add_widget(view('AccountNote', text=(
            'Contacto incluido: ' + contact.get('name', '') + ' · ' + contact.get('phone', '')
            if has_contact else 'Sin teléfono de contacto. Añádelo para que quien escanee pueda llamar a tu familia.')))
        def configure(*_):
            modal.dismiss()
            self.qr_contact_form(pet)
        body.add_widget(view('AccountAction', text='Editar contacto y privacidad del QR', callback=configure))
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
            qr_frame.children[0].reload()
            body.add_widget(qr_frame)
            body.add_widget(view(
                'QrExpiry',
                text='Visible en esta app hasta ' + expires.strftime('%d/%m/%Y') + '. Al escanear se muestra un texto de prueba.',
            ))
            body.add_widget(view('QrPrivacy'))
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
            profile = self.contact_profile()
            body.add_widget(view('AccountProfile', name=profile.get('name') or 'Completa tu perfil',
                                 detail=profile.get('phone') or 'Añade un teléfono de contacto'))
            action('Editar perfil', self.edit_contact_profile)
            action('Mis datos', partial(self.account_options, 'data'))
            action('Seguridad', partial(self.account_options, 'security'))
            if self.mobile.configured:
                action('Notificaciones y privacidad', self.mobile_preferences)
                action('Probar notificaciones', self.push_panel)
                action('Recordatorios automáticos', self.reminder_panel)
        else:
            if platform == 'android' and self.cloud.config.get('GOOGLE_SIGN_IN_ENABLED') is True:
                action('Continuar con Google', self.signin_google)
            action("Crear cuenta", partial(self.auth_form, True))
            action("Ya tengo cuenta", partial(self.auth_form, False))
            action('Mis datos', partial(self.account_options, 'data'))
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()

    def mobile_preferences(self):
        prefs = self.mobile.preferences()
        def submit(values):
            self.mobile.configure(values['notifications'] == 'Sí', values['analytics'] == 'Sí')
            if values['notifications'] == 'No' and self.cloud.user:
                self.network(lambda: PushClient(self.cloud, self.mobile).unregister(), lambda _: None)
        self.form('Notificaciones y privacidad', [
            ('notifications', '¿Recibir avisos de cuidados?', 'Sí' if prefs['notifications'] else 'No'),
            ('analytics', '¿Compartir estadísticas de uso?', 'Sí' if prefs['analytics'] else 'No')],
            submit, choices={'notifications': ('No', 'Sí'), 'analytics': ('No', 'Sí')}, persist=False,
            submit_text='Guardar preferencias',
            description='Son opcionales. Las estadísticas no incluyen nombres, teléfonos ni datos de tus mascotas.')

    def push_panel(self):
        modal, card = self.dialog('Avisos en este teléfono', 480)
        card.add_widget(view('AccountNote', text='Primero activa los avisos y acepta el permiso de Android. Luego envía una prueba, espera la confirmación y minimiza la app: el servidor la enviará 30 segundos después. El servidor permite una prueba por minuto. Activa tus cuidados desde Mi cuenta → Recordatorios automáticos.'))
        def act(operation, message):
            modal.dismiss()
            self.network(operation, lambda _: self.message('Avisos', message))
        push = PushClient(self.cloud, self.mobile)
        card.add_widget(view('AccountAction', text='Registrar este teléfono', callback=lambda *_: act(push.register, 'Teléfono vinculado a tu cuenta. Ya puedes enviar una prueba.')))
        card.add_widget(view('AccountPrimary', text='Probar en 30 segundos', callback=lambda *_: act(push.test, 'Prueba aceptada. Ahora minimiza la app o bloquea la pantalla. El servidor intentará enviarla en 30 segundos. Mantén internet y no fuerces la detención de la app.')))
        card.add_widget(view('AccountAction', text='Retirar este teléfono', callback=lambda *_: act(push.unregister, 'Este teléfono ya no recibirá avisos de tu cuenta.')))
        modal.open()

    def signin_google(self):
        try:
            url = self.google_auth.begin()
            if platform == 'android':
                from jnius import autoclass
                intent = autoclass('android.content.Intent')('android.intent.action.VIEW',
                                                            autoclass('android.net.Uri').parse(url))
                autoclass('org.kivy.android.PythonActivity').mActivity.startActivity(intent)
            else:
                webbrowser.open(url)
        except CloudError as exc:
            self.message('No se pudo acceder', str(exc))

    def google_intent(self, intent):
        uri = str(intent.getDataString() or '')
        if not uri.startswith('mimascota://auth/callback'):
            return
        Clock.schedule_once(lambda _: self.network(lambda: self.google_auth.finish(uri), self.auth_link_finished), 0)

    def auth_link_finished(self, result):
        self.authenticated(result)
        if self.google_auth.completed_flow == 'recovery':
            Clock.schedule_once(lambda _: self.recovered_password_form(), .2)

    def forgot_password(self, email=''):
        def submit(values):
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values['email']):
                raise ValueError('Escribe un correo válido.')
            self.network(lambda: self.google_auth.recover(values['email']),
                lambda _: self.message('Revisa tu correo', 'Si existe una cuenta con ese correo, recibirás un enlace. Ábrelo en este teléfono y vuelve a la app para elegir tu nueva contraseña.'))
        self.form('Recuperar contraseña', [('email', 'Correo electrónico', email)], submit,
                  persist=False, input_types={'email': 'mail'}, submit_text='Enviar enlace',
                  description='Abre el enlace en el mismo teléfono donde lo solicitas.')

    def recovered_password_form(self):
        def submit(values):
            if len(values['password']) < 8:
                raise ValueError('Usa una contraseña de al menos 8 caracteres.')
            if values['password'] != values['password_confirm']:
                raise ValueError('Las contraseñas no coinciden.')
            self.network(lambda: self.cloud.change_password(values['password']),
                lambda _: self.message('Contraseña actualizada', 'Tu nueva contraseña ya está lista.'))
        self.form('Tu nueva contraseña', [('password', 'Nueva contraseña', ''),
                  ('password_confirm', 'Repite la contraseña', '')], submit,
                  password=True, persist=False, submit_text='Guardar contraseña')

    def account_options(self, section):
        modal, card = self.dialog('Mis datos' if section == 'data' else 'Seguridad', 490)
        def action(label, callback):
            def run(*_):
                modal.dismiss()
                callback()
            card.add_widget(view('AccountAction', text=label, callback=run))
        if section == 'data':
            if self.cloud.user:
                action('Reintentar guardado', self.upload)
                action('Recuperar copia guardada', self.download)
                action('Traer mascotas del invitado', self.import_local)
            action('Exportar copia', self.export_backup)
        else:
            action('Cambiar contraseña', self.password_form)
            action('Cerrar sesión', self.logout)
        modal.open()

    def contact_profile(self):
        if not self.cloud.user:
            return {}
        metadata = self.cloud.user.get('user_metadata') or {}
        profile = metadata.get('contact_profile', {})
        if isinstance(profile, dict) and profile:
            return profile
        return {'name': metadata.get('full_name') or metadata.get('name') or ''}

    def edit_contact_profile(self):
        source = self.contact_profile()
        def submit(values):
            clean = contact_values(values)
            if not clean['name']:
                raise ValueError('Escribe tu nombre o el de la persona de contacto.')
            self.network(lambda: self.cloud.update_profile(clean), lambda _: self.account())
        self.form('Tu perfil', [('name', 'Nombre de contacto *', source.get('name', '')),
                  ('phone', 'Teléfono con código de país', source.get('phone', '')),
                  ('city', 'Comuna / ciudad (opcional, privada)', source.get('city', ''))], submit,
                  persist=False, submit_text='Guardar perfil', input_types={'phone': 'tel'}, hints={'phone': '+56 9 1234 5678'},
                  description='Se guarda en tu cuenta. Editar este perfil no cambia los QR ya generados; configura el contacto de cada mascota por separado.')

    def choose_qr_contact(self):
        if not self.data['pets']:
            self.prompt_register_pet('Configurar el contacto de su chapa')
            return
        options = {f'{i + 1}. {p["name"]}': p for i, p in enumerate(self.data['pets'])}
        self.form('¿Para qué mascota?', [('pet', 'Mascota', next(iter(options)))],
                  lambda values: self.qr_contact_form(options[values['pet']]),
                  choices={'pet': list(options)}, persist=False)

    def qr_contact_form(self, pet):
        source = pet.get('qr_contact', {}) or self.contact_profile()
        if not isinstance(source, dict):
            source = {}
        def submit(values):
            share = values['share_phone'] == 'Sí, incluir contacto'
            clean = contact_values(values, required=share)
            pet['qr_contact'] = dict(clean, share_phone=share)
        self.form('Contacto de ' + pet['name'], [
            ('share_phone', '¿Mostrar nombre y teléfono al escanear?', 'Sí, incluir contacto' if source.get('share_phone') else 'No, solo mascota'),
            ('name', 'Persona de contacto', source.get('name', '')),
            ('phone', 'Teléfono con código de país', source.get('phone', ''))], submit,
            choices={'share_phone': ('No, solo mascota', 'Sí, incluir contacto')},
            visible_when={'name': ('share_phone', 'Sí, incluir contacto'), 'phone': ('share_phone', 'Sí, incluir contacto')},
            input_types={'phone': 'tel'}, hints={'phone': '+56 9 1234 5678'},
            description='Elige quién puede llamar a tu familia. Para publicar cambios, abre Chapa → Más opciones → Actualizar ficha. Tu correo y dirección nunca aparecen en la ficha.')

    def password_form(self):
        def submit(values):
            if not values['current_password']:
                raise ValueError('Escribe tu contraseña actual.')
            if len(values['password']) < 8:
                raise ValueError('Usa una contraseña de al menos 8 caracteres.')
            if values['password'] != values['password_confirm']:
                raise ValueError('Las contraseñas no coinciden.')
            email = self.cloud.user['email']
            def change():
                if not self.cloud.authenticate(email, values['current_password']):
                    raise CloudError('No se pudo verificar tu contraseña actual.')
                return self.cloud.change_password(values['password'])
            self.network(change, lambda _: self.message('Contraseña actualizada', 'Usa la nueva contraseña la próxima vez que inicies sesión.'))
        self.form('Cambiar contraseña', [('current_password', 'Contraseña actual', ''),
                  ('password', 'Nueva contraseña', ''), ('password_confirm', 'Repite la nueva contraseña', '')],
                  submit, password=True, persist=False, submit_text='Actualizar contraseña')

    def auth_form(self, signup):
        if not self.cloud.configured:
            self.message("Conexión pendiente", "No podemos conectar tu cuenta ahora. Puedes seguir usando la app como invitado.")
            return
        def submit(v):
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v["email"]):
                raise ValueError("Escribe un correo válido.")
            if len(v["password"]) < (8 if signup else 1):
                raise ValueError("Usa una contraseña de al menos 8 caracteres.")
            profile = registration_values(v) if signup else None
            def finished(signed_in):
                if signup and not signed_in:
                    self.confirm_signup_email(v['email'], v['password'])
                else:
                    self.authenticated(signed_in)
            self.network(lambda: self.cloud.authenticate(v["email"], v["password"], signup, profile=profile), finished)
        fields = [('name', 'Tu nombre *', '')] if signup else []
        fields += [("email", "Correo electrónico *", ""), ("password", "Contraseña *", "")]
        if signup:
            fields.append(('password_confirm', 'Repite la contraseña *', ''))
        modal, entries = self.form("Crear cuenta" if signup else "Iniciar sesión", fields, submit, password=True, persist=False,
                  submit_text='Crear cuenta' if signup else 'Iniciar sesión',
                  input_types={'email': 'mail'}, description='Crea tu cuenta para guardar tus mascotas y probar su chapa.' if signup else 'Continúa con tus mascotas y sus cuidados.')
        if not signup:
            def recover(*_):
                email = entries['email'].text.strip()
                modal.dismiss()
                self.forgot_password(email)
            modal.children[0].add_widget(view('AccountAction', text='Olvidé mi contraseña', callback=recover))

    def confirm_signup_email(self, email, password):
        modal, card = self.dialog('Confirma tu correo', 340)
        card.children[-1].size_hint_y = None
        pending = {'email': email, 'password': password}
        modal.bind(on_dismiss=lambda *_: pending.clear())
        card.add_widget(view('AccountNote', text='Abre el mensaje de verificación que enviamos a '
                             + email + '. Después vuelve aquí para continuar.'))
        def continue_signin(*_):
            if self.busy or not pending:
                return
            def done(signed_in):
                if signed_in:
                    modal.dismiss()
                    self.authenticated(True)
            credentials = dict(pending)
            def signin():
                try:
                    return self.cloud.authenticate(credentials['email'], credentials['password'])
                finally:
                    credentials.clear()
            self.network(signin, done)
        def resend(*_):
            if self.busy or not pending:
                return
            email_to_resend = pending['email']
            self.network(lambda: self.cloud.resend_signup(email_to_resend),
                         lambda _: self.message('Revisa tu correo', 'Solicitamos un nuevo mensaje. Revisa también la carpeta de spam.'))
        card.add_widget(view('AccountPrimary', text='Ya confirmé mi correo', callback=continue_signin))
        card.add_widget(view('AccountAction', text='Reenviar mensaje', callback=resend))
        modal.open()

    def authenticated(self, signed_in, resumed=False):
        if not signed_in:
            self.message("Revisa tu correo", "Si el registro fue aceptado, recibirás un enlace para confirmar tu correo. Después vuelve a Mi Mascota e inicia sesión.")
            return
        user_id = str(uuid.UUID(self.cloud.user["id"]))
        has_guest_pets = self.data_file == self.guest_file and bool(self.data['pets'])
        self.switch_store(self.guest_file.parent / "accounts" / (user_id + ".json"))
        self.queue_backup()
        if not self.cloud.session_persisted:
            self.message("No se guardó el acceso", "Puedes usar tu cuenta ahora, pero no pudimos guardar la sesión en este dispositivo. Revisa el espacio disponible antes de cerrar la app.")
        if not resumed and self.mobile.configured and self.mobile.preferences()['notifications']:
            self.network(lambda: PushClient(self.cloud, self.mobile).register(), lambda _: None)
        if not resumed and has_guest_pets and not self.data['pets']:
            self.message("Tus mascotas siguen contigo", "Para traerlas a esta cuenta, abre Mi cuenta → Ajustes de cuenta → Datos y respaldos → Traer mascotas del invitado.")

    def switch_store(self, path):
        self._backup_blocked = False
        self.backup_status = "Guardado en este teléfono"
        self.store = LocalStore(path)
        self.data_file = self.store.path
        self.data = deepcopy(self.store.data)
        self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
        self.notified.clear()
        self._reminder_accepted = None
        self._reminder_conflict = False
        self.reminder_status = "Cambios pendientes de sincronizar" if self.data.get("reminder_dirty") else ""
        if not self.cloud.user:
            self.queue_reminders()
        self.show("Inicio")
        if hasattr(self, '_qr_owner'):
            self.refresh_qr_badge()
        if self.store.readonly:
            self.message("Archivo protegido", "No se pudo leer este espacio local. No se sobrescribirá. Revisa el archivo y su copia .bak.")

    def network(self, operation, callback):
        if getattr(self, "_reminder_running", False) or getattr(self, "_backup_running", False):
            Clock.schedule_once(lambda _: self.network(operation, callback), .5)
            return
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
        self.retry_backup()

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
                    from services.backup_sync import SyncJournal
                    SyncJournal(self.data_file).accept(incoming)
                except (OSError, ValueError):
                    self.message("No se pudo restaurar", "La copia de seguridad o el guardado fallaron. No se reemplazó tu estado local.")
                    return
                self.switch_store(self.data_file)
                self.queue_backup()
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
                self.message("Importación local lista", "Los registros se copiaron a tu cuenta. Se guardarán automáticamente cuando tengas internet. El original del invitado se conserva.")
        self.confirm("Importar invitado", "Copia las mascotas, rutinas e historial de este dispositivo a tu cuenta. Hazlo sólo si esos datos son tuyos. Los registros ya importados no se duplican.", transfer)

    def backup_file(self, prefix="copia"):
        folder = self.data_file.parent / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{prefix}-{care_now(self.data):%Y%m%d-%H%M%S-%f}.json'
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
            revoked = True
            try:
                PushClient(self.cloud, self.mobile).unregister()
            except CloudError:
                revoked = False
            finally:
                if self.mobile.configured:
                    try:
                        self.mobile.initialize().notifications(False)
                    except Exception:
                        revoked = False
            try:
                self.cloud.logout()
                return revoked
            except CloudError:
                return False
        def done(revoked):
            self.google_auth.cancel()
            self.switch_store(self.guest_file)
            if not revoked:
                self.message("Sesión cerrada en este equipo", "No pudimos cerrar la sesión en línea. Cuando tengas conexión, revisa tu cuenta.")
        self.network(leave, done)
