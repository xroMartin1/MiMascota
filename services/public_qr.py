"""Cliente de chapas web. No sustituye ni inicia automáticamente la prueba local."""
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID
import re
import segno
from services.cloud import CloudError


class PublicChapas:
    def __init__(self, cloud, site_url):
        parsed = urlparse(site_url or "")
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("El enlace de la chapa no está disponible ahora.")
        self.cloud = cloud
        self.site_url = site_url.rstrip("/")

    def existing(self, pet_id):
        if not isinstance(pet_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pet_id):
            raise ValueError("Identificador de mascota inválido.")
        rows = self.cloud.request("GET", "/rest/v1/pet_tags?select=pet_id&tag_kind=eq.trial&pet_id=eq."
                                  + pet_id + "&limit=1", authorized=True)
        if not isinstance(rows, list) or (rows and (
                not isinstance(rows[0], dict) or rows[0].get("pet_id") != pet_id)):
            raise CloudError("Respuesta de chapa inválida.")
        # Abrir la pantalla nunca emite una prueba. El servidor verifica el estado.
        return self.manage(pet_id, "sync") if rows else None

    def trial_status(self):
        result = self.cloud.request('POST', '/functions/v1/manage-tag', {'action': 'status'}, authorized=True)
        if not isinstance(result, dict) or type(result.get('used')) is not bool:
            raise CloudError('No pudimos comprobar tu prueba.')
        if result['used'] and (not isinstance(result.get('pet_id'), str) or result.get('status') not in ('active', 'expired', 'unavailable')):
            raise CloudError('No pudimos comprobar tu prueba.')
        return result

    def manage(self, pet_id, action="issue"):
        if not isinstance(pet_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pet_id):
            raise ValueError("Identificador de mascota inválido.")
        if action not in ("issue", "sync", "revoke"):
            raise ValueError("Operación de chapa inválida.")
        result = self.cloud.request("POST", "/functions/v1/manage-tag",
                                    {"pet_id": pet_id, "action": action}, authorized=True)
        try:
            code = UUID(result["scan_code"])
            created = datetime.fromisoformat(result["created_at"])
            expires = datetime.fromisoformat(result["expires_at"])
            if code.version != 4 or created.tzinfo is None or expires.tzinfo is None or expires <= created:
                raise ValueError
            if result["status"] not in ("active", "expired", "unavailable"):
                raise ValueError
        except (TypeError, KeyError, ValueError, AttributeError):
            raise CloudError("Respuesta de chapa inválida; no se creó una imagen QR.") from None
        return dict(scan_code=str(code), created_at=created.isoformat(), expires_at=expires.isoformat(),
                    status=result["status"], access_kind='paid' if result.get('access_kind') == 'paid' else 'trial', url=f"{self.site_url}/q/{code}")


def write_public_png(tag, path):
    if tag.get("status") != "active":
        raise ValueError("Esta chapa no está activa.")
    url = urlparse(tag.get("url", ""))
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("URL pública de chapa inválida.")
    try:
        code = UUID(tag["scan_code"])
        if code.version != 4 or url.path != f"/q/{code}":
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise ValueError("Token público de chapa inválido.") from None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    segno.make(tag["url"], error="m").save(str(path), scale=7, border=4,
                                          dark="#102F37", light="#FFFFFF")
    return path
