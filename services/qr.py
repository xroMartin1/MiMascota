"""Chapas de demostración locales. La caducidad pública requiere un servidor."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import segno
from services.profile import contact_values

TRIAL_DAYS = 14


def start_trial(trials, pet_id, now=None):
    """Un período por mascota: volver a abrir la vista nunca reinicia el reloj."""
    if pet_id in trials:
        return trials[pet_id]
    now = now or datetime.now(timezone.utc)
    trial = {
        "code": uuid.uuid4().hex,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(days=TRIAL_DAYS)).isoformat(),
    }
    trials[pet_id] = trial
    return trial


def trial_expired(trial, now=None):
    now = now or datetime.now(timezone.utc)
    return now >= datetime.fromisoformat(trial["expires_at"])


def preview_payload(pet, trial):
    """Contacto solo si la familia autorizó esta copia para esta mascota."""
    name = " ".join(pet["name"].split())[:48]
    species = " ".join(pet["kind"].split())[:32]
    contact = pet.get("qr_contact", {})
    public = "Esta es una prueba local. No permite contactar a la familia."
    if isinstance(contact, dict) and contact.get("share_phone") is True:
        clean = contact_values(contact, required=True)
        public = f"Contacto: {clean['name']}\nTeléfono: {clean['phone']}\nSi me encontraste, llama a mi familia."
    return ("MI MASCOTA | CHAPA DE PRUEBA\n"
            f"Mascota: {name}\n"
            f"Especie: {species}\n"
            f"Identificador: {trial['code'][:10].upper()}\n"
            + public)


def write_preview_png(pet, trial, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    segno.make(preview_payload(pet, trial), error="m").save(str(path), scale=7, border=4,
                                                              dark="#102F37", light="#FFFFFF")
    return path
