"""Auth and private backups. Android encrypts its session in the native vault."""
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse
import requests
from threading import RLock
from services.session_storage import SessionStorage


class CloudError(Exception):
    pass


class Supabase:
    def __init__(self, config_path=None, session_storage=None):
        config_path = config_path or Path(__file__).resolve().parents[1] / "config.json"
        self.config = {}
        try:
            self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if not isinstance(self.config, dict):
            self.config = {}
        self.url = os.getenv("SUPABASE_URL", self.config.get("SUPABASE_URL", "")).rstrip("/")
        self.key = os.getenv("SUPABASE_PUBLISHABLE_KEY", self.config.get("SUPABASE_PUBLISHABLE_KEY", ""))
        self.session = None
        self.session_storage = session_storage or SessionStorage()
        self.session_lock = RLock()
        self.session_persisted = True
        self.site_url = os.getenv("MIMASCOTA_SITE_URL", self.config.get(
            "MIMASCOTA_SITE_URL", "https://mi-mascota-web.vercel.app"))

    @property
    def configured(self):
        return urlparse(self.url).scheme == "https" and bool(urlparse(self.url).hostname) and self.key.startswith("sb_publishable_")

    @property
    def user(self):
        return self.session.get("user") if self.session else None

    def request(self, method, path, payload=None, authorized=False):
        if not self.configured:
            raise CloudError("La conexión con tu cuenta no está disponible ahora.")
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if authorized:
            with self.session_lock:
                if not self.session:
                    raise CloudError("Inicia sesión para usar la nube.")
                if self.session["expires_at"] <= time.time() + 60:
                    renewed = self.request("POST", "/auth/v1/token?grant_type=refresh_token",
                                           {"refresh_token": self.session["refresh_token"]})
                    self.set_session(renewed)
                headers["Authorization"] = "Bearer " + self.session["access_token"]
        try:
            response = requests.request(method, self.url + path, headers=headers, json=payload,
                                        timeout=(8, 20), allow_redirects=False)
        except requests.RequestException:
            raise CloudError("No se pudo conectar. Tus datos locales siguen disponibles; revisa internet e inténtalo otra vez.") from None
        if not response.ok:
            try:
                details = response.json()
                code = next((details.get(key) for key in ('code', 'error_code', 'error')
                             if isinstance(details.get(key), str)), None)
            except (ValueError, AttributeError):
                code = None
            push_errors = {
                'firebase_config': 'Los avisos no están disponibles ahora. Inténtalo más tarde.',
                'firebase_auth': 'No pudimos activar los avisos. Inténtalo más tarde.',
                'firebase_send': 'No pudimos enviar el aviso. Inténtalo más tarde.',
                'device_not_registered': 'Este teléfono dejó de recibir avisos. Vuelve a activarlos desde Notificaciones.',
                'plan_conflict': 'Otro dispositivo cambió el calendario. En Recordatorios automáticos puedes publicar los cuidados de este teléfono para reemplazarlo, después de revisar sus fechas.',
                'invalid_plan': 'Revisa la zona horaria y las fechas del calendario (máximo 500 cuidados).',
                'device_limit': 'Esta cuenta ya tiene cinco teléfonos registrados.',
            }
            if path == '/functions/v1/push-device' and isinstance(code, str) and code in push_errors:
                raise CloudError(push_errors[code])
            if code == 'email_not_confirmed':
                raise CloudError('Confirma tu correo antes de continuar. Revisa el mensaje de verificación.')
            if path == '/functions/v1/care-share':
                messages = {'unavailable': 'La invitación venció, ya fue usada o el acceso terminó.',
                            'member_limit': 'Esta mascota ya tiene tres personas invitadas.',
                            'pet_not_found': 'Guarda la mascota en tu cuenta antes de compartirla.'}
                raise CloudError(messages.get(code, 'No pudimos abrir los cuidados compartidos. Inténtalo más tarde.'))
            if path == '/functions/v1/manage-tag' and code in ('trial_already_used', 'trial_ended'):
                raise CloudError('Tu cuenta ya utilizó su única chapa de prueba de 14 días. No se puede iniciar otra para una mascota diferente.')
            if path.startswith('/auth/v1/token?grant_type=refresh_token') and response.status_code in (400, 401) and code in (
                    'refresh_token_not_found', 'refresh_token_already_used', 'session_not_found', 'session_expired', 'invalid_grant'):
                with self.session_lock:
                    if not self.session or self.session.get('refresh_token') == (payload or {}).get('refresh_token'):
                        self.session_storage.clear()
                        self.session = None
                        raise CloudError("Tu sesión dejó de ser válida. Inicia sesión de nuevo; tus mascotas siguen guardadas.")
            if "revision_conflict" in response.text:
                raise CloudError("La nube tiene otra versión. Restaura la copia de nube antes de volver a guardarla; tus cambios locales no se han borrado.")
            if response.status_code in (400, 401, 403, 422):
                raise CloudError("No pudimos completar la solicitud. Revisa tu correo y contraseña.")
            if response.status_code == 429:
                raise CloudError("Demasiados intentos. Espera unos minutos antes de repetir.")
            raise CloudError("No pudimos completar la operación. Inténtalo de nuevo más tarde.")
        try:
            return response.json() if response.content else {}
        except ValueError:
            raise CloudError("Respuesta no válida del servidor.") from None

    def set_session(self, result):
        if not result.get("access_token") or not result.get("refresh_token") or not result.get("user", {}).get("id"):
            raise CloudError("La sesión no es válida. Vuelve a iniciar sesión.")
        with self.session_lock:
            result = dict(result)
            result["expires_at"] = time.time() + result.get("expires_in", 3600)
            self.session = result
            self.cache_session()

    def cache_session(self):
        result = self.session
        if not result:
            return
        metadata = result['user'].get('user_metadata')
        profile = metadata.get('contact_profile', {}) if isinstance(metadata, dict) else {}
        if not isinstance(profile, dict):
            profile = {}
        if not profile.get('name') and isinstance(metadata, dict):
            name = metadata.get('full_name') or metadata.get('name')
            if isinstance(name, str) and len(name) <= 60:
                profile = dict(profile, name=name)
        profile = {key: value for key, maximum in [('name',60),('phone',40),('city',80)]
                   if isinstance((value := profile.get(key, '')), str) and len(value) <= maximum}
        cached_user = {'id': result['user']['id'], 'email': result['user'].get('email', ''),
                       'user_metadata': {'contact_profile': profile}}
        self.session_persisted = self.session_storage.write(json.dumps({'url': self.url, 'access_token': result['access_token'],
            'refresh_token': result['refresh_token'], 'expires_at': result['expires_at'], 'user': cached_user}))

    def restore_session(self):
        with self.session_lock:
            if self.session:
                return True  # Never replace a newer login with an older startup cache.
            saved = self.session_storage.read()
            if not saved:
                return False
            try:
                cached = json.loads(saved)
                if (not isinstance(cached, dict) or cached.get('url') != self.url or
                    not isinstance(cached.get('access_token'), str) or not cached['access_token'] or
                    not isinstance(cached.get('refresh_token'), str) or not cached['refresh_token'] or
                    type(cached.get('expires_at')) not in (int, float) or
                    not isinstance(cached.get('user'), dict) or not cached['user'].get('id')):
                    raise ValueError
                self.session = {key: cached[key] for key in ('access_token', 'refresh_token', 'expires_at', 'user')}
            except (ValueError, TypeError, KeyError):
                self.session_storage.clear()
                return False
            if self.session['expires_at'] > time.time() + 60:
                return True
            result = self.request('POST', '/auth/v1/token?grant_type=refresh_token', {'refresh_token': self.session['refresh_token']})
            self.set_session(result)
            return True

    def retry_session_cache(self):
        with self.session_lock:
            if self.session and not self.session_persisted:
                self.cache_session()

    def authenticate(self, email, password, signup=False, profile=None):
        path = "/auth/v1/signup" if signup else "/auth/v1/token?grant_type=password"
        payload = {"email": email, "password": password}
        if signup and profile is not None:
            payload["data"] = {"contact_profile": profile}
        result = self.request("POST", path, payload)
        if result.get("access_token"):
            self.set_session(result)
            return True
        return False

    def resend_signup(self, email):
        return self.request('POST', '/auth/v1/resend', {'type': 'signup', 'email': email})

    def update_profile(self, profile):
        result = self.request("PUT", "/auth/v1/user", {"data": {"contact_profile": profile}}, authorized=True)
        self.session["user"] = result
        self.cache_session()
        return result

    def change_password(self, password):
        result = self.request("PUT", "/auth/v1/user", {"password": password}, authorized=True)
        self.session["user"] = result
        self.cache_session()
        return result

    def upload(self, data):
        return self.request("POST", "/rest/v1/rpc/save_petcare_state",
                            {"expected_revision": data["cloud_revision"], "payload": data}, authorized=True)

    def download(self):
        if not self.user:
            raise CloudError("Inicia sesión para usar la nube.")
        rows = self.request("GET", "/rest/v1/petcare_state?select=data,revision", authorized=True)
        return rows[0] if rows else None

    def logout(self):
        with self.session_lock:
            try:
                if self.session:
                    self.request("POST", "/auth/v1/logout?scope=local", authorized=True)
            finally:
                self.session = None
                self.session_storage.clear()
