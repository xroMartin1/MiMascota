"""Supabase Auth + copia privada con control de revisiones. Tokens sólo en memoria."""
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse
import requests


class CloudError(Exception):
    pass


class Supabase:
    def __init__(self, config_path=None):
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

    @property
    def configured(self):
        return urlparse(self.url).scheme == "https" and bool(urlparse(self.url).hostname) and self.key.startswith("sb_publishable_")

    @property
    def user(self):
        return self.session.get("user") if self.session else None

    def request(self, method, path, payload=None, authorized=False):
        if not self.configured:
            raise CloudError("Configura la URL y la clave publicable de Supabase en config.json.")
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if authorized:
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
            if "revision_conflict" in response.text:
                raise CloudError("La nube tiene otra versión. Restaura la copia de nube antes de volver a guardarla; tus cambios locales no se han borrado.")
            if response.status_code in (400, 401, 403, 422):
                raise CloudError("No se pudo completar la solicitud. Revisa tus credenciales, confirma tu correo y comprueba la configuración del proyecto.")
            if response.status_code == 429:
                raise CloudError("Demasiados intentos. Espera unos minutos antes de repetir.")
            raise CloudError("El servicio no pudo completar la operación. Verifica el esquema SQL y vuelve a intentarlo.")
        try:
            return response.json() if response.content else {}
        except ValueError:
            raise CloudError("Respuesta no válida del servidor.") from None

    def set_session(self, result):
        if not result.get("access_token") or not result.get("refresh_token") or not result.get("user", {}).get("id"):
            raise CloudError("La sesión no es válida. Vuelve a iniciar sesión.")
        result["expires_at"] = time.time() + result.get("expires_in", 3600)
        self.session = result

    def authenticate(self, email, password, signup=False):
        path = "/auth/v1/signup" if signup else "/auth/v1/token?grant_type=password"
        result = self.request("POST", path, {"email": email, "password": password})
        if result.get("access_token"):
            self.set_session(result)
            return True
        return False

    def upload(self, data):
        return self.request("POST", "/rest/v1/rpc/save_petcare_state",
                            {"expected_revision": data["cloud_revision"], "payload": data}, authorized=True)

    def download(self):
        if not self.user:
            raise CloudError("Inicia sesión para usar la nube.")
        rows = self.request("GET", "/rest/v1/petcare_state?select=data,revision", authorized=True)
        return rows[0] if rows else None

    def logout(self):
        try:
            if self.session:
                self.request("POST", "/auth/v1/logout?scope=local", authorized=True)
        finally:
            self.session = None
