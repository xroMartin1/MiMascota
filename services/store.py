"""Persistencia local atómica y validación, independiente de Kivy y de la red."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import shutil
import uuid

DATE_FORMAT = "%Y-%m-%d %H:%M"
KINDS = ("Cuidado", "Medicamento", "Vacuna", "Desparasitación", "Cita")


def empty_data():
    return {"version": 2, "pets": [], "routines": [], "events": [], "cloud_revision": 0}


def normalize(value):
    if not isinstance(value, dict):
        raise ValueError("Archivo de datos inválido")
    data = empty_data()
    data.update(deepcopy(value))
    for collection in ("pets", "routines", "events"):
        if not isinstance(data[collection], list):
            raise ValueError("Lista de datos inválida")
        seen = set()
        for index, item in enumerate(data[collection]):
            if not isinstance(item, dict):
                raise ValueError("Registro inválido")
            # IDs estables para volver a importar archivos antiguos sin duplicados.
            item.setdefault("id", uuid.uuid5(uuid.NAMESPACE_URL, collection + str(index) + json.dumps(item, sort_keys=True)).hex)
            if not isinstance(item["id"], str) or not item["id"] or item["id"] in seen:
                raise ValueError("Identificador inválido o duplicado")
            seen.add(item["id"])
            keys = {"pets": ("name", "kind", "breed", "age", "weight", "chip"),
                    "routines": ("title", "detail", "time", "icon"),
                    "events": ("title", "detail", "pet")}[collection]
            if any(not isinstance(item.get(k), str) for k in keys):
                raise ValueError("Campos de datos inválidos")
            if collection == "routines":
                item.setdefault("pet", "")
                item.setdefault("kind", "Cuidado")
                item.setdefault("repeat", "No")
                item.setdefault("due_at", "")
                item.setdefault("done", False)
                if not isinstance(item["done"], bool) or not isinstance(item["pet"], str) or not isinstance(item["due_at"], str):
                    raise ValueError("Actividad inválida")
                if item["kind"] not in KINDS or item["repeat"] not in ("No", "Diaria", "Semanal"):
                    raise ValueError("Tipo o repetición inválida")
                if item["due_at"]:
                    datetime.strptime(item["due_at"], DATE_FORMAT)
    if type(data["cloud_revision"]) is not int or data["cloud_revision"] < 0:
        raise ValueError("Versión de nube inválida")
    data["version"] = 2
    return data


class LocalStore:
    def __init__(self, path):
        self.path = Path(path)
        self.readonly = False
        self.data = empty_data()
        if self.path.exists():
            try:
                self.data = normalize(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError, KeyError):
                self.readonly = True

    def save(self, data):
        if self.readonly:
            raise ValueError("No se pudo leer el archivo original. Se conservó intacto; revisa el archivo y su copia .bak.")
        clean = normalize(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(clean, stream, ensure_ascii=False, indent=2)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_suffix(".bak"))
        temp.replace(self.path)
        self.data = deepcopy(clean)


def pet_values(values):
    result = {k: str(values.get(k, "")).strip() for k in ("name", "kind", "breed", "age", "weight", "chip")}
    if not result["name"] or not result["kind"]:
        raise ValueError("Escribe el nombre y la especie.")
    if result["weight"] and result["weight"] != "—":
        try:
            weight = float(result["weight"].replace(",", "."))
        except ValueError:
            raise ValueError("El peso debe ser un número mayor que cero.") from None
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("El peso debe ser un número mayor que cero.")
        result["weight"] = str(weight)
    result["breed"] = result["breed"] or result["kind"]
    result["weight"] = result["weight"] or "—"
    result["age"] = result["age"] or "Sin registrar"
    return result


def complete_task(data, task, now=None):
    """Una toma completada genera historial; la recurrencia avanza sin duplicar tareas."""
    now = now or datetime.now()
    if task["done"]:
        task["done"] = False
        return
    data["events"].append({"id": uuid.uuid4().hex, "pet": task["pet"], "title": task["title"],
                           "detail": task["detail"], "date": now.strftime(DATE_FORMAT),
                           "kind": task["kind"], "task_id": task["id"], "status": "Completado"})
    if task["repeat"] != "No" and task["due_at"]:
        due = datetime.strptime(task["due_at"], DATE_FORMAT)
        step = timedelta(days=1 if task["repeat"] == "Diaria" else 7)
        due += step * max(1, (now - due) // step + 1)
        task["due_at"] = task["time"] = due.strftime(DATE_FORMAT)
    else:
        task["done"] = True


def pending(data, now=None, due_only=False):
    now = now or datetime.now()
    tasks = [r for r in data["routines"] if not r["done"]]
    if due_only:
        tasks = [r for r in tasks if r["due_at"] and datetime.strptime(r["due_at"], DATE_FORMAT) <= now]
    return sorted(tasks, key=lambda r: r["due_at"] or "9999")


def import_guest(target, guest):
    result = deepcopy(target)
    for key in ("pets", "routines", "events"):
        known = {v["id"] for v in result[key]}
        result[key].extend(deepcopy(v) for v in guest[key] if v["id"] not in known)
    return normalize(result)
