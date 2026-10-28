"""Browser authentication with PKCE, including recovery across Android restarts."""
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse
from services.cloud import CloudError
from services.session_storage import SessionStorage

CALLBACK = 'mimascota://auth/callback'


class GoogleAuth:
    def __init__(self, cloud, storage=None):
        self.cloud = cloud
        self.storage = storage or SessionStorage('flow')
        self.pending = None
        self.completed_flow = None
        try:
            saved = json.loads(self.storage.read() or '{}')
            if (isinstance(saved, dict) and saved.get('url') == cloud.url
                    and saved.get('flow') in ('google', 'recovery')
                    and isinstance(saved.get('verifier'), str) and len(saved['verifier']) >= 43
                    and isinstance(saved.get('state'), str) and len(saved['state']) >= 24
                    and type(saved.get('deadline')) in (int, float) and saved['deadline'] > time.time()):
                self.pending = saved
        except (ValueError, TypeError):
            pass

    def prepare(self, flow):
        if not self.cloud.configured:
            raise CloudError('El acceso a tu cuenta no está disponible ahora.')
        verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        self.pending = dict(verifier=verifier, state=state, flow=flow, url=self.cloud.url,
                            deadline=time.time() + (3600 if flow == 'recovery' else 600))
        self.storage.write(json.dumps(self.pending))
        return CALLBACK + '?' + urlencode({'state': state}), challenge

    def begin(self):
        redirect, challenge = self.prepare('google')
        return self.cloud.url + '/auth/v1/authorize?' + urlencode(dict(
            provider='google', redirect_to=redirect,
            code_challenge=challenge, code_challenge_method='s256'))

    def recover(self, email):
        redirect, challenge = self.prepare('recovery')
        try:
            self.cloud.request('POST', '/auth/v1/recover?' + urlencode({'redirect_to': redirect}),
                               {'email': email, 'code_challenge': challenge, 'code_challenge_method': 's256'})
        except CloudError:
            self.cancel()
            raise
        return True

    def finish(self, callback):
        parsed = urlparse(callback)
        query = parse_qs(parsed.query)
        pending = self.pending
        if (not pending or time.time() >= pending['deadline']
                or parsed.scheme != 'mimascota' or parsed.netloc != 'auth' or parsed.path != '/callback'
                or parsed.fragment or query.get('state') != [pending['state']]
                or len(query.get('code', [])) != 1 or not query['code'][0]):
            raise CloudError('El enlace no pudo completarse. Solicita uno nuevo desde la app.')
        result = self.cloud.request('POST', '/auth/v1/token?grant_type=pkce',
                                    {'auth_code': query['code'][0], 'code_verifier': pending['verifier']})
        self.cloud.set_session(result)
        self.completed_flow = pending['flow']
        self.cancel()
        return True

    def cancel(self):
        if self.pending:
            self.pending.clear()
        self.pending = None
        self.storage.clear()
