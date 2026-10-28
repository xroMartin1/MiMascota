"""Plan de avisos: solo identificadores, fechas y zona, sin datos médicos."""
from services.cloud import CloudError
from services.push import PushClient

ZONES = ('America/Santiago', 'America/Punta_Arenas', 'Pacific/Easter', 'America/Buenos_Aires',
         'America/Lima', 'America/Bogota', 'America/Mexico_City', 'Europe/Madrid', 'UTC')

ZONE_LABELS = {'America/Santiago': 'Chile · Santiago', 'America/Punta_Arenas': 'Chile · Punta Arenas',
               'Pacific/Easter': 'Chile · Isla de Pascua', 'America/Buenos_Aires': 'Argentina · Buenos Aires',
               'America/Lima': 'Perú · Lima', 'America/Bogota': 'Colombia · Bogotá',
               'America/Mexico_City': 'México · Ciudad de México', 'Europe/Madrid': 'España · Madrid', 'UTC': 'Hora universal (UTC)'}

def zone_label(zone):
    return ZONE_LABELS.get(zone, zone.rsplit('/',1)[-1].replace('_',' ') + ' · hora del teléfono')

def suggested_zone():
    from kivy.utils import platform
    if platform == 'android':
        from jnius import autoclass
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        zone = str(autoclass('java.util.TimeZone').getDefault().getID())
        try:
            ZoneInfo(zone)
            return zone
        except (ZoneInfoNotFoundError,ValueError):
            return 'UTC'
    return 'America/Santiago'  # Sugerencia visible: el usuario debe confirmarla.

def plan_payload(data):
    settings = data.get('reminder_settings', {'enabled': False, 'timezone': 'UTC'})
    return dict(enabled=settings['enabled'], timezone=settings['timezone'],
                routines=sorted([dict(id=r['id'], due_at=r['due_at'], repeat=r['repeat'], done=r['done'])
                                 for r in data['routines']], key=lambda r: r['id']))

class ReminderClient:
    def __init__(self, cloud, mobile):
        self.cloud, self.mobile = cloud, mobile

    def publish(self, payload, revision, replace=False):
        push = PushClient(self.cloud, self.mobile)
        if payload['enabled']:
            push.register()
        _, _, device = push.identity()
        if replace:
            status = self.cloud.request('POST', '/functions/v1/push-device',
                                        dict(action='plan_status',device_id=device), authorized=True)
            revision = status['revision']
        result = self.cloud.request('POST', '/functions/v1/push-device',
                                   dict(action='plan_save',device_id=device,revision=revision,payload=payload), authorized=True)
        if type(result.get('revision')) is not int:
            raise CloudError('El servidor no confirmó la revisión del calendario.')
        return result
