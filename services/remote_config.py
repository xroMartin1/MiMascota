"""A public care tip from Supabase, with a validated device-only JSON cache."""
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from services.cloud import CloudError

DEFAULT_TIP = 'Revisa que tu mascota tenga agua fresca y un lugar cómodo para descansar.'
TIP_PATH = '/rest/v1/app_public_config?key=eq.home_care_tip&select=message,updated_at&limit=1'


def valid_message(value):
    if not isinstance(value, str):
        raise ValueError('Consejo inválido')
    value = value.strip()
    if not 1 <= len(value) <= 200 or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Consejo inválido')
    return value


class RemoteConfig:
    def __init__(self, cloud, cache_path):
        self.cloud = cloud
        self.path = Path(cache_path)
        self.message = DEFAULT_TIP
        self.source = 'default'
        self.updated_at = ''
        self.checked_at = ''
        self.cache_saved = False
        try:
            if self.path.stat().st_size > 4096:
                return
            cached = json.loads(self.path.read_text(encoding='utf-8'))
            if cached.get('origin') != cloud.url:
                return
            self.message = valid_message(cached.get('message'))
            self.updated_at = str(cached.get('updated_at', ''))[:80]
            self.checked_at = str(cached.get('checked_at', ''))[:80]
            self.source = 'cache'
            self.cache_saved = True
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    @property
    def status(self):
        return {'remote': 'Actualizado en línea', 'cache': 'Último consejo guardado',
                'default': 'Consejo disponible sin conexión'}[self.source]

    def refresh(self):
        """No authentication, personal data, or executable remote content."""
        if not self.cloud.configured:
            return False
        try:
            result = self.cloud.request('GET', TIP_PATH)
            if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
                return False
            message = valid_message(result[0].get('message'))
            stamp = result[0].get('updated_at')
            if not isinstance(stamp, str) or len(stamp) > 80:
                return False
        except (CloudError, ValueError, TypeError, OSError):
            # Includes CloudError; any failed refresh keeps the accepted value.
            return False
        self.message, self.updated_at = message, stamp
        self.checked_at = datetime.now(timezone.utc).isoformat()
        self.source = 'remote'
        self.cache_saved = False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(origin=self.cloud.url, message=message,
                                           updated_at=stamp, checked_at=self.checked_at),
                                       ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(self.path)
            self.cache_saved = True
        except OSError:
            pass  # A full/read-only disk must not hide the received tip.
        return True
