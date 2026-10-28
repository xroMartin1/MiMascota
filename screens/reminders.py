"""Sincronización opcional con cola local y control de versiones entre teléfonos."""
from copy import deepcopy
from threading import Thread
from kivy.clock import Clock
from screens.views import view
from services.reminders import ReminderClient, plan_payload, suggested_zone, ZONES, zone_label
from services.cloud import CloudError

class ReminderFeatures:
    def queue_reminders(self, *_):
        if not self.cloud.user or not self.mobile.configured:
            return
        if not self.data.get('reminder_settings', {}).get('enabled') and not self.data.get('reminder_dirty'):
            return
        if plan_payload(self.data) == getattr(self, '_reminder_accepted', None):
            return
        self.data['reminder_dirty'] = True
        self.store.save(self.data)
        if getattr(self, '_reminder_running', False):
            return
        if getattr(self, '_reminder_timer', None):
            self._reminder_timer.cancel()
        self._reminder_timer = Clock.schedule_once(lambda _: self.sync_reminders(), 1)

    def sync_reminders(self, replace=False, feedback=False):
        if getattr(self, '_reminder_running', False):
            if feedback:
                Clock.schedule_once(lambda _: self.sync_reminders(replace,feedback), .5)
            return
        if not self.cloud.user or not self.mobile.configured:
            return
        if not feedback and (not self.data.get('reminder_dirty') or getattr(self,'_reminder_conflict',False)):
            return
        if self.busy or getattr(self, "_backup_running", False):
            Clock.schedule_once(lambda _: self.sync_reminders(replace,feedback), 2)
            return
        payload=plan_payload(deepcopy(self.data))
        revision=self.data.get('reminder_revision',0)
        owner=self.cloud.user['id']
        path=self.data_file
        self._reminder_running=True
        self.reminder_status='Sincronizando avisos…'
        def run():
            try:
                result=ReminderClient(self.cloud,self.mobile).publish(payload,revision,replace)
                error=None
            except CloudError as exc:
                result=None; error=str(exc)
            except Exception:
                result=None; error='No se confirmó el calendario. Revisa internet y los permisos de avisos.'
            def finish(_):
                self._reminder_running=False
                if self.data_file!=path or not self.cloud.user or self.cloud.user['id']!=owner:
                    return
                if error:
                    self._reminder_conflict='Otro dispositivo' in error
                    self.reminder_status='Cambios pendientes de sincronizar'
                    if feedback:
                        self.message('Avisos sin confirmar',error+' Los avisos anteriores pueden seguir activos hasta sincronizar.')
                else:
                    self._reminder_conflict=False
                    self._reminder_accepted=payload
                    self.data['reminder_revision']=result['revision']
                    self.data['reminder_dirty']=plan_payload(self.data)!=payload
                    self.reminder_status='Avisos sincronizados' if payload['enabled'] else 'Avisos automáticos desactivados'
                    if payload['enabled']:
                        bridge, activity = self.mobile.native()
                        self._reminder_token = str(bridge.token(activity))
                    if feedback:
                        self.message('Calendario actualizado','Los avisos de tus cuidados ya están actualizados.' if payload['enabled'] else 'El calendario automático se desactivó en el servidor.')
                try:
                    self.store.save(self.data)
                except (OSError,ValueError):
                    self.message('No se pudo guardar','El servidor puede haber actualizado el calendario; vuelve a sincronizar para confirmar la revisión.')
                if self.active == 'Rutina':
                    self.show('Rutina')
                if not error and self.data['reminder_dirty']:
                    self.queue_reminders()
            Clock.schedule_once(finish)
        Thread(target=run,daemon=True).start()

    def reminder_panel(self):
        if not self.require_account(): return
        settings=self.data.get('reminder_settings',{'enabled':False,'timezone':'UTC'})
        zone=settings['timezone'] if settings['enabled'] else suggested_zone()
        options = {zone_label(z): z for z in dict.fromkeys((zone,)+ZONES)}
        def submit(values):
            self.data['reminder_settings']={'enabled':values['enabled']=='Sí','timezone':options[values['timezone']]}
            self.data['reminder_dirty']=True
            self.store.save(self.data)
            self.queue_backup()
            self.sync_reminders(replace=True,feedback=True)
        self.form('Recordatorios automáticos',[
            ('enabled','¿Enviar avisos con la app minimizada?','Sí' if settings['enabled'] else 'No'),
            ('timezone','¿Dónde se programan tus cuidados?',zone_label(zone))],submit,
            choices={'enabled':('No','Sí'),'timezone':tuple(options)},persist=False,
            submit_text='Guardar recordatorios',
            description='Te avisaremos aunque minimices la app. Confirma la zona horaria de tus cuidados. Al guardar, se usarán los cuidados de este teléfono para los avisos de tu cuenta, reemplazando los de otro teléfono si los hubiera. Necesitas internet para actualizar los cambios.')

    def retry_reminders(self, *_):
        if (self.cloud.user and self.mobile.configured and self.data.get('reminder_settings',{}).get('enabled')
                and self.mobile.preferences()['notifications']):
            bridge, activity = self.mobile.native()
            token = str(bridge.token(activity))
            if token and token != getattr(self, '_reminder_token', ''):
                self.data['reminder_dirty'] = True
        self.cloud.retry_session_cache()
        if self.data.get('reminder_dirty'):
            self.sync_reminders()
