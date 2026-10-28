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
            raise CloudError('Los avisos push están disponibles en Android con Firebase configurado.')
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
                return self.cloud.request('POST', '/functions/v1/push-device',
                                          dict(action='register', device_id=device, token=token), authorized=True)
            time.sleep(.25)
        raise CloudError('Firebase todavía está preparando el teléfono. Revisa internet y vuelve a intentarlo en unos segundos.')

    def test(self):
        self.register()
        _, _, device = self.identity()
        return self.cloud.request('POST', '/functions/v1/push-device',
                                  dict(action='test', device_id=device), authorized=True)

    def unregister(self):
        if not self.cloud.user or not self.mobile.configured:
            return
        _, _, device = self.identity()
        return self.cloud.request('POST', '/functions/v1/push-device',
                                  dict(action='unregister', device_id=device), authorized=True)
