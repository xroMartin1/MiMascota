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
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.metrics import dp
from screens import theme as design
from pathlib import Path
from screens.views import view, PetFormPreview, ViewSpinner
from services.store import LocalStore, normalize, pet_values, complete_task, pending, import_guest, DATE_FORMAT, KINDS, care_now
from services.cloud import CloudError
from services.push import PushClient
from services.reminders import zone_label
from services.profile import contact_values, registration_values
from services.qr import start_trial, trial_expired, write_preview_png, TRIAL_DAYS
from screens.public_tag import PublicTagFeatures
from screens.reminders import ReminderFeatures
from screens.date_field import DateField
from services.pet_profiles import BREEDS, pet_details, age_text
from services.agenda import agenda


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
    return day + date.strftime(', %H:%M')


class CareFeatures(ReminderFeatures, PublicTagFeatures):
    def save(self, *, completed=None):
        try:
            self.store.save(self.data)
            self.update_premium_badge()
            if completed:
                self.record_care_completion(*completed)
            self.observe_measurement()
            self.queue_reminders()
            if hasattr(self, "queue_backup"):
                self.queue_backup()
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.track_event('usage_error', code='storage')
            self.data = deepcopy(self.store.data)
            self.message("No se pudo guardar", "Tus datos anteriores se conservaron. Inténtalo de nuevo." if isinstance(exc, ValueError) else "Revisa el espacio disponible e inténtalo de nuevo.")
            return False

    def home(self):
        pets = self.data['pets']
        tasks = pending(self.data)
        late = pending(self.data, due_only=True)
        if not pets:
            self.content.add_widget(view('HomeEmptyPets'))
            self.content.add_widget(view('HomeRegisterPet', callback=self.register_pet))
        else:
            self.content.add_widget(view('HomeSection', title='Mis mascotas', action='Añadir', callback=self.register_pet))
            for pet in pets[:3]:
                detail = pet_details(pet)
                self.content.add_widget(view('HomePetRow', name=pet['name'], kind=pet['kind'], breed=pet['breed'], detail=detail,
                                             callback=partial(self.profile, pet)))
            if len(pets) > 3:
                self.content.add_widget(view('HomeViewPets', callback=partial(self.show, 'Mascotas')))
            self.content.add_widget(view('HomeSection', title='Cuidados', action='Ver todos', callback=partial(self.show, 'Rutina')))
            if late:
                self.content.add_widget(view('HomeNote', text=f'{len(late)} cuidado pendiente de completar' if len(late) == 1 else f'{len(late)} cuidados pendientes de completar'))
            if tasks:
                for task in tasks[:3]:
                    when = readable_date(task['due_at'], care_now(self.data)) if task['due_at'] else 'Sin fecha'
                    self.content.add_widget(view('UxRow', title=task['title'], bg=design.LIME if task is tasks[0] else design.WHITE,
                        detail=self.pet_name(task['pet']) + ', ' + when, icon='calendar-clock',
                        callback=partial(self.task_detail, task)))
            else:
                self.content.add_widget(view('HomeNote', text='No tienes cuidados pendientes. Puedes añadir un paseo, una vacuna o una cita.'))
                self.content.add_widget(view('AccountAction', text='Añadir cuidado', callback=self.add_routine))
        self.content.add_widget(view('HomeQrCard', callback=partial(self.show, 'Chapa')))
        self.content.add_widget(self.care_tip())

    def pet_name(self, pet_id):
        return next((p["name"] for p in self.data["pets"] if p["id"] == pet_id), "General")

    def chip_text(self, pet):
        if pet["chip"]:
            return pet["chip"]
        return {"Sí": "Número pendiente", "No": "No"}.get(pet.get("chip_status"), "Sin registrar")

    def weight_text(self, pet):
        return f'{pet["weight"]} kg' if pet["weight"] != "—" else "Sin registrar"

    def pets(self):
        count = len(self.data["pets"])
        self.heading("Mis mascotas", f'{count} {"mascota registrada" if count == 1 else "mascotas registradas"}')
        self.content.add_widget(view('PetsRegister', callback=self.register_pet))
        if not self.data["pets"]:
            self.content.add_widget(view('PetsEmpty'))
        for pet in self.data['pets']:
            detail = pet_details(pet)
            self.content.add_widget(view('HomePetRow', name=pet['name'], kind=pet['kind'], breed=pet['breed'], detail=detail,
                                         callback=partial(self.profile, pet)))
        if self.data['pets']:
            self.content.add_widget(view('UxRow', title='Gestionar chapa', detail='Revisa los datos que ven al escanearla',
                                         icon='tag-outline', bg=design.SURFACE, callback=partial(self.show, 'Chapa')))

    def register_pet(self, *_, pet=None):
        species = ("Perro", "Gato", "Conejo", "Ave", "Pez", "Reptil", "Hámster", "Otro")
        known_kind = pet.get("kind", "") if pet else ""
        selected_kind = next((kind for kind in species[:-1] if kind.casefold() == known_kind.casefold()),
                             "Otro" if known_kind else "Seleccionar especie")
        old_chip = pet.get("chip", "") if pet else ""
        chip_status = pet.get("chip_status", "Sí" if old_chip else "No sé") if pet else "No sé"
        old_age = pet.get("age", "") if pet else ""
        old_breed = pet.get('breed', 'Sin registrar') if pet else 'Sin registrar'
        def breed_choices(kind):
            options = ('Sin registrar',) + BREEDS.get(kind, ()) + ('Mestizo', 'Otra raza')
            if pet and kind.casefold() == known_kind.casefold() and old_breed not in options:
                options += (old_breed,)
            return options
        fields = [
            ("name", "Nombre *", pet.get("name", "") if pet else ""),
            ("kind", "Especie *", selected_kind),
            ("custom_kind", "¿Qué especie? *", known_kind if selected_kind == "Otro" else ""),
            ("breed", "Raza", old_breed),
            ("custom_breed", "¿Qué raza?", old_breed if old_breed == 'Otra raza' else ''),
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
            if values['breed'] == 'Otra raza':
                values['breed'] = values['custom_breed'].strip()
                if not values['breed']:
                    raise ValueError('Escribe la raza o elige Mestizo.')
            clean = pet_values(values)
            if pet:
                target = next((p for p in self.data['pets'] if p['id'] == pet['id']), None)
                if target is None:
                    raise ValueError('Esta mascota ya no está disponible.')
                target.update(clean)
            else:
                self.data["pets"].append(dict(clean, id=uuid.uuid4().hex))
                self.selected_pet = self.data["pets"][-1]["id"]
        preview = PetFormPreview(kind=selected_kind, breed=old_breed)
        _, entries = self.form("Editar mascota" if pet else "Nueva mascota", fields, submit,
                  choices={"kind": ("Seleccionar especie",) + species,
                           "breed": breed_choices(selected_kind),
                           "chip_status": ("No sé", "Sí", "No")},
                  visible_when={"custom_kind": ("kind", "Otro"), "custom_breed": ("breed", "Otra raza"), "chip": ("chip_status", "Sí")},
                  hints={"name": "Ej.: Luna", "custom_kind": "Ej.: Tortuga", "age": "Ej.: 3 años",
                         "weight": "Ej.: 4,2", "chip": "Número de la cartilla"},
                  input_types={"weight": "number", "chip": "number"}, preview=preview, operation='pet')
        def update_breeds(_, kind):
            options = breed_choices(kind)
            entries['breed'].values = list(options)
            if entries['breed'].text not in options:
                entries['breed'].text = 'Sin registrar'
        entries['kind'].bind(text=update_breeds)
        def update_preview(*_):
            preview.kind = entries['custom_kind'].text if entries['kind'].text == 'Otro' else entries['kind'].text
            preview.breed = entries['custom_breed'].text if entries['breed'].text == 'Otra raza' else entries['breed'].text
        for key in ('kind', 'breed', 'custom_kind', 'custom_breed'):
            entries[key].bind(text=update_preview)
        update_preview()

    def profile(self, pet, *_):
        modal, outer = self.dialog(pet["name"], 510)
        scroll, card = view('AccountScroll'), view('QrInfoBody')
        scroll.add_widget(card)
        outer.add_widget(scroll)
        modal.ids.dialog_title.font_size = '30sp'
        card.add_widget(view('PetHero', kind=pet['kind'], breed=pet['breed'],
                             age=age_text(pet['age']) or 'Sin registrar', weight=self.weight_text(pet)))
        def act(callback, *_):
            modal.dismiss()
            callback()
        tasks = [task for task in pending(self.data) if task['pet'] == pet['id']]
        next_task = tasks[0] if tasks else None
        card.add_widget(view('PetNextCare', title=next_task['title'] if next_task else 'Sin cuidados pendientes',
            date=readable_date(next_task['due_at'] or next_task['time'], care_now(self.data)) if next_task else '',
            action='Ver cuidado' if next_task else 'Añadir cuidado',
            callback=partial(act, partial(self.task_detail, next_task)) if next_task else partial(act, partial(self.add_pet_care, pet['id']))))
        card.add_widget(view('ProfileHealth', callback=partial(act, partial(self.select_pet, pet['id']))))
        card.add_widget(view('ProfileQr', callback=partial(act, partial(self.qr_info, pet))))
        card.add_widget(view('ProfileEdit', callback=partial(act, partial(self.register_pet, pet=pet))))
        if pet.get('chip'):
            card.add_widget(view('AccountNote', text='Microchip: ' + pet['chip']))
        card.add_widget(view('ProfileDelete', callback=partial(act, partial(self.delete_pet, pet))))
        def fit_profile(*_):
            header = outer.children[-1]
            desired = card.minimum_height + header.height + outer.padding[1] + outer.padding[3] + outer.spacing
            modal.size_hint_y = min(.88, desired / Window.height)
        resize = Clock.create_trigger(fit_profile, 0)
        card.bind(minimum_height=resize)
        modal.bind(size=resize, on_open=resize)
        modal.open()

    def add_pet_care(self, pet_id):
        self.selected_pet = pet_id
        self.add_routine()

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
        self.heading("Rutina", "Paseos, medicamentos y citas")
        self.content.add_widget(view('RoutineAdd', callback=self.add_routine))
        self.content.add_widget(view('RoutineImageBanner', source=str(Path(__file__).resolve().parents[1] / 'assets/MascotsBanner.png')))
        if self.cloud.user and self.mobile.configured:
            status = ('Avisos pendientes de actualizar' if self.data.get('reminder_dirty') else
                      getattr(self, 'reminder_status', '') or ('Avisos automáticos activos' if self.data.get('reminder_settings', {}).get('enabled') else 'Avisos automáticos desactivados'))
            self.content.add_widget(view('UxRow', title='Recordatorios', detail=status, icon='bell-outline', callback=lambda *_: self.reminder_panel()))
        groups, completed, total = agenda(self.data, care_now(self.data))
        self.content.add_widget(view('DayProgress', text=f'{len(completed)} de {total} cuidados de hoy' if total else 'Sin cuidados para hoy',
                                     progress=len(completed)/total if total else 0))
        done_ids = {task['id'] for task in groups['Completados']}
        for title, tasks in groups.items():
            recurring = [event for task_id, event in completed.items()
                         if task_id not in done_ids] if title == 'Completados' else []
            if not tasks and not recurring:
                continue
            self.content.add_widget(view('StorySection', text=title))
            for task in tasks:
                self.content.add_widget(self.task_card(task))
            for event in recurring:
                self.content.add_widget(view('StoryEvent', title=event['title'], date=readable_date(event['date'], care_now(self.data)),
                                             detail=self.pet_name(event['pet']), icon='check', task_id=event['task_id'], completed=True))
        if not self.data['routines'] and not completed:
            self.content.add_widget(view('RoutineEmpty'))

    def task_card(self, task):
        stamp = readable_date(task['due_at'] or task['time'], care_now(self.data)).rsplit(', ', 1)
        entry = view('AgendaEntry', task_id=task['id'], day=stamp[0], time=stamp[1] if len(stamp) > 1 else '', done=task['done'])
        card = entry.ids.body
        card.add_widget(view('CareTaskHeading', text=task['title'],
                             icon={'Cuidado': 'paw', 'Medicamento': 'pill', 'Vacuna': 'needle', 'Cita': 'calendar-heart'}.get(task['kind'], 'heart-pulse')))
        card.add_widget(view('HomeNote', text=self.pet_name(task['pet']) + ', ' + task['kind']))
        actions = view('CareTaskActions', callback=partial(self.task_detail, task))
        if task["kind"] == "Cuidado":
            actions.add_widget(view(
                'CareTaskToggle',
                task_id=task['id'],
                icon='check-circle' if task['done'] else 'check',
                text='Reabrir' if task['done'] else 'Hecho',
                callback=partial(self.toggle_routine, task['id']),
            ))
        card.add_widget(actions)
        return entry

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
                target = next((r for r in self.data['routines'] if r['id'] == task['id']), None)
                if target is None:
                    raise ValueError('Este cuidado ya no está disponible.')
                target.update(item)
            else:
                self.data["routines"].append(dict(item, id=uuid.uuid4().hex, done=False))
        source = task or {}
        fields = [("pet", "Mascota", current), ("kind", "Tipo de cuidado", source.get("kind", kind)),
                  ("title", "Actividad o medicamento *", source.get("title", "")),
                  ("detail", "Detalles / pauta indicada por tu veterinario", source.get("detail", "")),
                  ("due_at", ("Fecha y hora, " + zone_label(self.data["reminder_settings"]["timezone"]) if self.data.get("reminder_settings", {}).get("enabled") else "Fecha y hora"), source.get("due_at") or default_time),
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
                  hints={"title": "Ej.: Paseo de la tarde", "due_at": "AAAA-MM-DD HH:MM"}, operation='care')

    def task_detail(self, task, *_):
        modal, card = self.dialog("Detalle del cuidado", 530)
        details = view('TaskDetailDetails', text=task['detail'] or 'Sin detalles adicionales')
        card.add_widget(view('TaskTitle', text=task['title']))
        card.add_widget(view(
            'TaskSummary',
            text=f"{self.pet_name(task['pet'])}, {task['kind']}\n{task['time']}\nRepetición: {task['repeat']}",
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
        def fit_details(*_):
            fixed = sum(child.height for child in card.children if child is not scroll)
            desired = details.height + fixed + card.padding[1] + card.padding[3] + card.spacing * (len(card.children) - 1)
            modal.size_hint_y = min(.88, desired / Window.height)
        resize = Clock.create_trigger(fit_details, 0)
        details.bind(height=resize)
        modal.bind(size=resize, on_open=resize)
        modal.open()

    def toggle_routine(self, task_id, *_):
        task = next(r for r in self.data["routines"] if r["id"] == task_id)
        was_done = task['done']
        due_at = task['due_at']
        complete_task(self.data, task)
        if self.save(completed=(task_id, due_at, was_done)):
            self.show(self.active)
            matches = [w for w in self.content.children if w.context.get('task_id') == task_id]
            entry = next((w for w in matches if w.context.get('completed')), matches[0] if matches else None)
            if entry:
                self.reveal(entry)
                button = next((w for w in entry.walk() if hasattr(w, 'icon') and w.context.get('task_id') == task_id), None)
                if button and not was_done and self.motion_enabled():
                    button.visual_scale = .88
                    Animation(visual_scale=1, duration=.2, t='out_cubic').start(button)
            self.saved_feedback('Cuidado pendiente' if was_done else 'Cuidado realizado')

    def health(self):
        self.heading("Salud", "Vacunas, tratamientos e historial")
        if not self.data["pets"]:
            self.content.add_widget(view('HealthEmptyPets'))
            self.content.add_widget(view('HealthRegisterPet', callback=self.register_pet))
            return
        if self.selected_pet not in [p["id"] for p in self.data["pets"]]:
            self.selected_pet = self.data["pets"][0]["id"]
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        pet = next(p for p in self.data['pets'] if p['id'] == self.selected_pet)
        summary = ('1 registro en su historial' if len(events) == 1 else f'{len(events)} registros en su historial') if events else 'Aún no hay registros'
        card = view(
            'HealthSummary',
            name=self.pet_name(self.selected_pet),
            kind=pet['kind'],
            breed=pet['breed'],
            weight='Peso registrado: ' + self.weight_text(pet) if pet['weight'] != '—' else '',
            summary=summary,
            export=lambda *_: self.export_health_report(),
        )
        if len(self.data['pets']) > 1:
            card.ids.health_name.add_widget(view('HealthChange', callback=self.change_health_pet))
        self.content.add_widget(card)
        self.content.add_widget(view('HealthAddEvent', callback=self.add_event))
        self.content.add_widget(view('HealthHistory', callback=self.history))
        if events:
            self.content.add_widget(view('StorySection', text='Su historia'))
            for event in sorted(reversed(events), key=lambda item: item.get('date', ''), reverse=True)[:3]:
                self.content.add_widget(self.story_event(event))
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

    def change_health_pet(self, *_):
        modal, card = self.dialog('Elige una mascota', 480)
        scroll, entries = view('AccountScroll'), view('HeadingBox')
        for pet in self.data['pets']:
            def choose(*_, pet_id=pet['id']):
                modal.dismiss()
                self.select_pet(pet_id)
            detail = pet_details(pet)
            entries.add_widget(view('HealthPetOption', name=pet['name'], kind=pet['kind'], breed=pet['breed'], detail=detail,
                                   selected=pet['id'] == self.selected_pet, callback=choose))
        scroll.add_widget(entries)
        card.add_widget(scroll)
        def fit(*_):
            header = card.children[-1]
            desired = entries.minimum_height + header.height + card.padding[1] + card.padding[3] + card.spacing
            modal.size_hint_y = min(.88, desired / Window.height)
        resize = Clock.create_trigger(fit, 0)
        entries.bind(minimum_height=resize)
        modal.bind(size=resize, on_open=resize)
        modal.open()

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
                target = next((e for e in self.data['events'] if e['id'] == event['id']), None)
                if target is None:
                    raise ValueError('Este registro ya no está disponible.')
                target.update(v)
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
            hints={"title": "Ej.: Control anual", "date": "AAAA-MM-DD HH:MM"}, operation='health')

    def history(self, *_):
        modal, card = self.dialog("Historial médico", 580)
        modal.size_hint_y = .88
        scroll = view('HistoryScroll')
        entries = view('HistoryEntries')
        events = [e for e in self.data["events"] if e["pet"] == self.selected_pet]
        if not events:
            modal.size_hint_y = None
            scroll.size_hint_y = None
            scroll.height = dp(70)
            entries.add_widget(view('HistoryEmpty'))
        for event in sorted(reversed(events), key=lambda e: e.get("date", ""), reverse=True):
            frame = self.story_event(event)
            entries.add_widget(frame)
            item = frame.ids.body
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
        scroll.add_widget(entries)
        card.add_widget(scroll)
        modal.open()

    def story_event(self, event):
        return view('StoryEvent', title=event['title'],
                    date=event.get('kind', 'Registro') + '\n' + readable_date(event.get('date', 'Sin fecha'), care_now(self.data)), detail=event.get('detail', ''),
                    icon={'Vacuna':'needle','Medicamento':'pill','Cita':'calendar-heart','Control':'heart-pulse'}.get(event.get('kind'), 'clipboard-check-outline'))

    def form(self, title, fields, submit, choices=None, password=False, persist=True,
             visible_when=None, hints=None, input_types=None, templates=None, date_shortcuts=None, description=None, submit_text=None, preview=None, operation=None):
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
            if preview is not None:
                inputs.add_widget(preview)
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
        modal._measurement_operation = operation
        modal._measurement_attempt = False
        def measured_result(result):
            if operation and modal._measurement_attempt:
                self.track_event('save_result', operation=operation, result=result)
                modal._measurement_attempt = False
        modal._measurement_result = measured_result
        def clear_error(*_):
            error.text = ""
        for entry in entries.values():
            entry.bind(text=clear_error)
        def save(*_):
            if self.busy or getattr(modal, '_network_pending', False):
                return
            error.text = ''
            if operation:
                self.track_event('save_attempt', operation=operation)
                modal._measurement_attempt = True
            pets_before = len(self.data['pets'])
            values = {key: field.text if "password" in key else field.text.strip() for key, field in entries.items()}
            try:
                self._submitting_form = modal
                try:
                    reason = submit(values)
                finally:
                    self._submitting_form = None
                if reason:
                    raise ValueError(reason)
                if getattr(modal, '_network_pending', False):
                    return
                if persist and not self.save():
                    measured_result('failed')
                    error.text = 'No se guardaron los cambios. Puedes volver a intentarlo.'
                    return
            except (ValueError, KeyError) as exc:
                measured_result('validation')
                if operation:
                    self.track_event('usage_error', code='validation')
                error.text = str(exc)
                return
            measured_result('success')
            if operation == 'pet' and len(self.data['pets']) > pets_before:
                self.track_event('pet_saved')
            modal.dismiss()
            if persist:
                self.show(self.active)
                self.saved_feedback('Cambios guardados')
        button = view('FormSubmit', text=submit_text or ('Continuar' if not persist else 'Guardar'), callback=save)
        card.add_widget(button)
        modal.ids.form_error = error
        modal.ids.form_submit = button
        modal.ids.form_inputs = inputs
        def close_form(*_):
            measured_result('abandoned')
            for entry in list(entries.values()) + list(modal.walk()):
                if isinstance(entry, ViewSpinner):
                    entry.is_open = False
                    Animation.cancel_all(entry, 'arrow_angle')
                    entry.arrow_angle = 0
            if preview is not None:
                for widget in preview.walk():
                    Animation.cancel_all(widget, 'opacity')
                    widget.opacity = 1
        modal.bind(on_dismiss=close_form)
        def fit_form(*_):
            fixed = sum(child.height for child in card.children if child is not scroll)
            desired = inputs.minimum_height + fixed + card.padding[1] + card.padding[3] + card.spacing * (len(card.children) - 1)
            modal.size_hint_y = min(.88, desired / Window.height)
        resize = Clock.create_trigger(fit_form, 0)
        inputs.bind(minimum_height=resize)
        error.bind(height=resize)
        modal.bind(size=resize, on_open=resize)
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
            content.add_widget(view('NotificationDate', text=f"{self.pet_name(task['pet'])}, {task['time']}"))
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
            'Contacto incluido: ' + contact.get('name', '') + ', ' + contact.get('phone', '')
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
                text='VISTA PREVIA, ' + str(TRIAL_DAYS) + ' DÍAS DESDE SU PRIMERA APERTURA',
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
            for title, path in (("Frente, nombre de la mascota", front_path),
                                ("Reverso, QR ilustrativo", back_path)):
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
        modal, card = self.dialog("Mi cuenta" if user else "Tu cuenta", 600)
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
            self.set_statistics(values['analytics'] == 'Sí')
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
        card.add_widget(view('AccountNote', text='Activa las notificaciones del teléfono y envía un aviso para comprobar que lo recibes. Puedes hacer una prueba por minuto.'))
        def act(operation, message):
            modal.dismiss()
            self.network(operation, lambda _: self.message('Avisos', message))
        push = PushClient(self.cloud, self.mobile)
        card.add_widget(view('AccountAction', text='Activar avisos', callback=lambda *_: act(push.register, 'Ya puedes comprobar si recibes los avisos.')))
        card.add_widget(view('AccountPrimary', text='Probar en 30 segundos', callback=lambda *_: act(push.test, 'Sal de la app o bloquea la pantalla. Intentaremos enviarte un aviso en 30 segundos. Mantén la conexión a internet.')))
        card.add_widget(view('AccountAction', text='Desactivar avisos', callback=lambda *_: act(push.unregister, 'Este teléfono ya no recibirá avisos de tu cuenta.')))
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
            self._backup_label = view('UxCaption', text=self.backup_status)
            card.add_widget(self._backup_label)
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
                  description='Para cambiar el contacto de una chapa, edítalo desde Chapa.', operation='account')

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
            target = next((p for p in self.data['pets'] if p['id'] == pet['id']), None)
            if target is None:
                raise ValueError('Esta mascota ya no está disponible.')
            target['qr_contact'] = dict(clean, share_phone=share)
        self.form('Contacto de ' + pet['name'], [
            ('share_phone', '¿Mostrar nombre y teléfono al escanear?', 'Sí, incluir contacto' if source.get('share_phone') else 'No, solo mascota'),
            ('name', 'Persona de contacto', source.get('name', '')),
            ('phone', 'Teléfono con código de país', source.get('phone', ''))], submit,
            choices={'share_phone': ('No, solo mascota', 'Sí, incluir contacto')},
            visible_when={'name': ('share_phone', 'Sí, incluir contacto'), 'phone': ('share_phone', 'Sí, incluir contacto')},
            input_types={'phone': 'tel'}, hints={'phone': '+56 9 1234 5678'},
            description='Después de guardar, pulsa Actualizar ficha en Chapa. Tu correo y dirección no se publican.')

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
                  input_types={'email': 'mail'})
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
        self.pause_measurement()
        self._backup_blocked = False
        self.backup_status = "Guardado en este teléfono"
        self.store = LocalStore(path)
        self.data_file = self.store.path
        self.data = deepcopy(self.store.data)
        self.start_measurement()
        self.start_premium_status()
        self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
        self.notified.clear()
        self._reminder_accepted = None
        self._reminder_conflict = False
        self.reminder_status = "Recordatorios pendientes de actualizar" if self.data.get("reminder_dirty") else ""
        if not self.cloud.user:
            self.queue_reminders()
        self.show("Inicio")
        if hasattr(self, '_qr_owner'):
            self.refresh_qr_badge()
        if self.store.readonly:
            self.message("Archivo protegido", "No pudimos abrir tus datos guardados. Los archivos se conservaron. Revisa tu copia de seguridad antes de continuar.")

    def network(self, operation, callback, *, _form=None):
        form = _form or getattr(self, '_submitting_form', None)
        if form is not None and not form._is_open:
            return
        if self.busy:
            if form is not None:
                Clock.schedule_once(lambda _: self.network(operation, callback, _form=form), .5)
            return
        if form is not None:
            form._network_pending = True
            form.ids.form_submit.disabled = True
            form.ids.form_submit.text = 'Procesando…'
            form.ids.form_inputs.disabled = True
        if getattr(self, "_reminder_running", False) or getattr(self, "_backup_running", False):
            Clock.schedule_once(lambda _: self.network(operation, callback, _form=form), .5)
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
                result, error = None, "No pudimos completar la acción. Tus datos siguen guardados."
            def finish(_):
                wait.dismiss()
                self.busy = False
                self.shell.disabled = False
                if form is not None:
                    form._network_pending = False
                    form.ids.form_submit.disabled = False
                    form.ids.form_submit.text = form.ids.form_submit.context['text']
                    form.ids.form_inputs.disabled = False
                def failed(message):
                    if form is not None and hasattr(form, '_measurement_result'):
                        form._measurement_result('failed')
                    if form is not None and form._is_open:
                        form.ids.form_error.text = message
                    else:
                        self.message('No se completó', message)
                if error:
                    self.track_event('usage_error', code='network')
                    failed(error)
                else:
                    try:
                        callback(result)
                        if form is not None:
                            if hasattr(form, '_measurement_result'):
                                form._measurement_result('success')
                            form.dismiss()
                    except (OSError, ValueError, KeyError, TypeError):
                        failed('No pudimos completar la acción. Tus datos anteriores se conservaron.')
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
                    self.message("No se pudo restaurar", "La copia de seguridad o el guardado fallaron. Tus datos anteriores se conservaron.")
                    return
                self.switch_store(self.data_file)
                self.queue_backup()
            self.confirm("Restaurar copia", f'La copia contiene {len(incoming["pets"])} mascotas y reemplazará los datos de esta cuenta en el teléfono. Guardaremos una copia de los datos actuales antes de continuar.', restore)
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
                self.message("Mascotas añadidas", "Tus mascotas y cuidados se añadieron a esta cuenta. Se guardarán cuando tengas conexión.")
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
            self.message("No se pudo exportar", "Revisa el espacio disponible e inténtalo de nuevo.")

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
