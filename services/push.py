"""Registro y prueba de un dispositivo propio. No guarda tokens en JSON ni logs."""
import time
from services.cloud import CloudError


class PushClient:
    def __init__(self, cloud, mobile):
        self.cloud, self.mobile = cloud, mobile

    def identity(self):
        if not self.cloud.user:
            raise CloudError('Inicia sesión para vincular los avisos a tu cuenta.')
        if not self.mobile.configured:
            raise CloudError('Los avisos no están disponibles en este dispositivo.')
        bridge, activity = self.mobile.native()
        return bridge, activity, str(bridge.deviceId(activity))

    def register(self):
        bridge, activity, device = self.identity()
        if not bridge.canNotify(activity):
            raise CloudError('Activa los avisos en Notificaciones y privacidad y permite las notificaciones de Android.')
        self.mobile.initialize().notifications(True)
        for _ in range(32):
            token = str(bridge.token(activity))
            if token:
                result = self.cloud.request('POST', '/functions/v1/push-device',
                                            dict(action='register', device_id=device, token=token), authorized=True)
                self.mobile._push_registration = (self.cloud.user['id'], token, time.monotonic())
                return result
            time.sleep(.25)
        raise CloudError('No pudimos activar los avisos todavía. Revisa tu conexión e inténtalo de nuevo.')

    def refresh_registration(self):
        if not self.cloud.user or not self.mobile.configured:
            return False
        bridge, activity = self.mobile.native()
        if not bridge.canNotify(activity):
            return False
        token = str(bridge.token(activity))
        previous = self.mobile.__dict__.get('_push_registration')
        if (token and previous and previous[:2] == (self.cloud.user['id'], token)
                and time.monotonic() - previous[2] < 86400):
            return False
        self.register()
        return True

    def test(self):
        self.register()
        _, _, device = self.identity()
        return self.cloud.request('POST', '/functions/v1/push-device',
                                  dict(action='test', device_id=device), authorized=True)

    def unregister(self):
        if not self.cloud.user or not self.mobile.configured:
            return
        self.mobile.__dict__.pop('_push_registration', None)
        _, _, device = self.identity()
        return self.cloud.request('POST', '/functions/v1/push-device',
                                  dict(action='unregister', device_id=device), authorized=True)
