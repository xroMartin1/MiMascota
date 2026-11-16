"""Quiet account backup synchronization; local care remains usable offline."""
from copy import deepcopy
from threading import Thread
from kivy.clock import Clock
from services.backup_sync import payload, merge, synchronize, SyncJournal, SyncConflict
from services.cloud import CloudError


class BackupFeatures:
    def start_backup(self):
        self._backup_running = False
        self._backup_blocked = False
        self.backup_status = 'Guardado en este teléfono'
        self._backup_event = None
        self._backup_clock = Clock.schedule_interval(self.retry_backup, 45)

    def queue_backup(self, *_):
        if self.cloud.user and not self._backup_blocked:
            self.backup_status = 'Cambios guardados aquí · esperando conexión'
            if self._backup_event:
                self._backup_event.cancel()
            self._backup_event = Clock.schedule_once(self.retry_backup, 2)

    def retry_backup(self, *_):
        if (not self.cloud.user or self._backup_running or self._backup_blocked or self.busy
                or getattr(self, '_reminder_running', False) or self.store.readonly):
            return
        owner, path = self.cloud.user['id'], self.data_file
        snapshot = payload(self.data)
        try:
            journal = SyncJournal(path)
        except (OSError, ValueError, KeyError, TypeError):
            self._backup_blocked = True
            self.backup_status = 'Revisa tu copia guardada antes de continuar'
            return
        self._backup_running = True
        self.backup_status = 'Guardando en tu cuenta…'
        self.refresh_backup_status()
        def run():
            try:
                result, revision = synchronize(self.cloud, snapshot, journal.base)
                error = None
            except SyncConflict as exc:
                result, revision, error = None, 0, exc
            except Exception as exc:
                result, revision, error = None, 0, exc
            def done(_):
                self._backup_running = False
                if not self.cloud.user or self.cloud.user['id'] != owner or self.data_file != path:
                    return
                if error:
                    self._backup_blocked = isinstance(error, SyncConflict)
                    self.backup_status = ('Hay cambios que revisar · tus datos siguen aquí' if self._backup_blocked
                                          else 'Guardado aquí · se enviará al recuperar conexión')
                else:
                    try:
                        # Include edits made while the worker was sending the snapshot.
                        current = payload(self.data)
                        combined = merge(snapshot, current, result)
                        updated = deepcopy(self.data)
                        updated.update(combined)
                        updated['cloud_revision'] = revision
                        changed_care = updated['routines'] != self.data['routines'] or updated['reminder_settings'] != self.data['reminder_settings']
                        if changed_care:
                            updated['reminder_dirty'] = True
                        self.store.save(updated)
                        self.data = deepcopy(self.store.data)
                        journal.accept(result)
                        self.backup_status = 'Todo guardado en tu cuenta'
                        self.queue_reminders()
                        if combined != result:
                            self.queue_backup()
                        if combined != current:
                            self.selected_pet = self.data['pets'][0]['id'] if self.data['pets'] else None
                            self.show(self.active)
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        self._backup_blocked = isinstance(exc, SyncConflict)
                        self.backup_status = 'Tus cambios siguen aquí · revisa las copias' if self._backup_blocked else 'Guardado aquí · pendiente de enviar'
                self.refresh_backup_status()
            Clock.schedule_once(done)
        Thread(target=run, daemon=True).start()

    def refresh_backup_status(self):
        if self.active == 'Cuenta' and hasattr(self, '_backup_label'):
            self._backup_label.text = self.backup_status

    def backup_options(self, *_):
        if self._backup_blocked:
            self.message('Revisa tus copias', 'Tus cambios están protegidos en este teléfono. En Ajustes de cuenta → Datos y respaldos puedes exportarlos y recuperar la copia de tu cuenta después de revisarla.')
        else:
            self.retry_backup()
