"""Simple account and notice pages, with infrequent actions tucked into settings."""
from datetime import datetime, timezone
from math import ceil
from functools import partial
from pathlib import Path
from threading import Thread
from uuid import uuid4
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from screens.views import ViewCard, view
from services.cloud import CloudError
from services.qr_inbox import QrInbox
from services.store import pending
from services.public_qr import PublicChapas, write_public_png
from services.care_share import CareShare
import webbrowser


class UxPress(ButtonBehavior, ViewCard):
    callback = ObjectProperty(None, allownone=True)
    def on_release(self):
        if self.callback:
            self.callback(self)

Factory.register('UxPress', cls=UxPress)
_loaded = False


class UxFeatures:
    def start_ux(self):
        global _loaded
        if not _loaded:
            Builder.load_file(str(Path(__file__).with_suffix('.kv')))
            _loaded = True
        self.google_available = self.cloud.config.get('GOOGLE_SIGN_IN_ENABLED') is True
        self._notice_rows = []
        self._notice_archived = False
        self._notice_loading = False
        self._notice_error = ''
        self._notice_timer = Clock.schedule_interval(self.refresh_notices, 30)
        Clock.schedule_once(self.restore_account, .1)
        Clock.schedule_once(self.check_google_provider, .2)

    def check_google_provider(self, *_):
        if not self.cloud.configured:
            return
        def run():
            try:
                result = self.cloud.request('GET', '/auth/v1/settings')
                available = result.get('external', {}).get('google') is True
            except Exception:
                return
            def done(_):
                self.google_available = available
                if self.active == 'Cuenta' and not self.cloud.user:
                    self.show('Cuenta')
            Clock.schedule_once(done)
        Thread(target=run, daemon=True).start()

    def restore_account(self, *_):
        if not self.cloud.configured:
            return
        def restore():
            try:
                restored = self.cloud.restore_session()
            except CloudError:
                restored = self.cloud.user is not None  # Offline retains local access to the account.
            if restored:
                Clock.schedule_once(lambda _: self.authenticated(True, resumed=True) if self.data_file == self.guest_file else None)
        Thread(target=restore, daemon=True).start()

    def account(self, *_):
        self.show('Cuenta')

    def render_account(self):
        user = self.cloud.user
        if not user:
            self.heading('Tu cuenta', 'Regístrate o inicia sesión para guardar tus mascotas y sus cuidados.')
            if self.google_available:
                self.content.add_widget(view('AccountPrimary', text='Continuar con Google', callback=lambda *_: self.signin_google()))
            self.content.add_widget(view('AccountPrimary', text='Crear cuenta', callback=lambda *_: self.auth_form(True)))
            self.content.add_widget(view('UxRow', title='Iniciar sesión', detail='Ya tengo una cuenta', icon='login', callback=lambda *_: self.auth_form(False)))
            return
        self.heading('Mi cuenta', '')
        name = self.contact_profile().get('name') or 'Mi perfil'
        self.content.add_widget(view('UxProfile', name=name, email=user.get('email', ''), callback=lambda *_: self.edit_contact_profile()))
        self._backup_label = view('UxCaption', text=self.backup_status)
        self.content.add_widget(self._backup_label)
        if self._backup_blocked:
            self.content.add_widget(view('UxRow', title='Revisar copias', detail='Tus cambios están protegidos', icon='cloud-alert-outline', callback=self.backup_options))
        if self.mobile.configured:
            self.content.add_widget(view('UxRow', title='Notificaciones', detail='Permisos y recordatorios', icon='bell-outline', callback=lambda *_: self.notice_preferences()))
        self.content.add_widget(view('UxRow', title='Cuidados compartidos', detail='Invita a alguien de confianza', icon='account-group-outline', callback=lambda *_: self.open_care_sharing()))
        self.content.add_widget(view('UxRow', title='Ajustes de cuenta', detail='Seguridad y opciones de datos', icon='cog-outline', callback=lambda *_: self.account_settings()))

    def account_settings(self):
        modal, outer = self.dialog('Ajustes de cuenta', 430)
        modal.size_hint_y = .85
        scroll, card = view('AccountScroll'), view('QrInfoBody')
        scroll.add_widget(card)
        outer.add_widget(scroll)
        def action(title, icon, callback):
            def run(*_):
                modal.dismiss()
                callback()
            card.add_widget(view('UxRow', title=title, detail='', icon=icon, callback=run))
        action('Cambiar contraseña', 'lock-outline', self.password_form)
        action('Recuperar contraseña por correo', 'email-outline', lambda: self.forgot_password(self.cloud.user.get('email', '')))
        action('Datos y respaldos', 'database-outline', partial(self.account_options, 'data'))
        action('Chapa y suscripción', 'qrcode', self.plan_info)
        action('Cerrar sesión', 'logout', self.logout)
        modal.open()

    def notice_preferences(self):
        modal, card = self.dialog('Notificaciones', 430)
        def action(title, icon, callback):
            def run(*_):
                modal.dismiss()
                callback()
            card.add_widget(view('UxRow', title=title, detail='', icon=icon, callback=run))
        action('Permisos del teléfono', 'bell-outline', self.mobile_preferences)
        action('Recordatorios automáticos', 'calendar-clock', self.reminder_panel)
        action('Comprobar un aviso', 'bell-check-outline', self.push_panel)
        modal.open()

    def notifications_center(self, *_):
        self._notice_archived = False
        self.show('Avisos')
        self.refresh_notices(force=True)

    def refresh_notices(self, *_ , force=False):
        if self.active != 'Avisos' or not self.cloud.user or self._notice_loading or self.busy:
            return
        owner, archived = self.qr_owner(), self._notice_archived
        self._notice_loading = True
        if force:
            self.render_notices(clear=True)
        def fetch():
            try:
                result, error = QrInbox(self.cloud).list(archived), ''
            except CloudError:
                result, error = None, 'No pudimos actualizar los mensajes.'
            def done(_):
                self._notice_loading = False
                if self.qr_owner() != owner:
                    return
                if self._notice_archived != archived:
                    self.refresh_notices(force=True)
                    return
                self._notice_error = error
                if result is not None:
                    self._notice_rows = result['threads']
                    self._notice_cursor = result.get('next_cursor')
                    self._qr_unread = result['unread']
                    self.set_qr_badge()
                if self.active == 'Avisos':
                    self.render_notices(clear=True)
            Clock.schedule_once(done)
        Thread(target=fetch, daemon=True).start()

    def render_notices(self, clear=False):
        if clear:
            self.content.clear_widgets()
        self.content.add_widget(view('UxToolbar', title='Archivados' if self._notice_archived else 'Avisos',
            left_icon='archive-arrow-up-outline' if self._notice_archived else 'archive-outline', left=lambda *_: self.toggle_archived(),
            right_icon='refresh', right=lambda *_: self.refresh_notices(force=True)))
        if self._notice_error:
            self.content.add_widget(view('UxCaption', text=self._notice_error))
        if self._notice_loading:
            self.content.add_widget(view('UxLoading'))
        rows = self._notice_rows if self.cloud.user else []
        if rows:
            self.content.add_widget(view('UxSection', text='MENSAJES'))
            for row in rows:
                date = datetime.fromisoformat(row['updated_at']).astimezone().strftime('%d/%m · %H:%M')
                self.content.add_widget(view('UxNotice', title=row['pet_name'], detail=row['preview'], date=date,
                    unread=bool(row['unread']), icon='message-outline', callback=lambda *_, r=row: self.open_qr_conversation(r['id'])))
        elif not self._notice_loading:
            self.content.add_widget(view('UxCaption', text='No tienes mensajes archivados.' if self._notice_archived else 'Aún no has recibido mensajes de tu chapa.'))
        if getattr(self, '_notice_cursor', None):
            self.content.add_widget(view('UxRow', title='Ver anteriores', detail='', icon='chevron-down', callback=lambda *_: self.load_more_notices()))
        tasks = pending(self.data, due_only=True) if not self._notice_archived else []
        if tasks:
            self.content.add_widget(view('UxSection', text='CUIDADOS PENDIENTES'))
            for task in tasks:
                self.content.add_widget(view('UxNotice', title=task['title'], detail=self.pet_name(task['pet']), date=task['time'],
                    unread=False, icon='calendar-clock', callback=lambda *_, t=task: self.task_detail(t)))
        if not self.cloud.user:
            self.content.add_widget(view('UxRow', title='Iniciar sesión', detail='Para recibir mensajes de tu chapa', icon='account-outline', callback=self.account))

    def toggle_archived(self):
        self._notice_archived = not self._notice_archived
        self._notice_rows, self._notice_cursor = [], None
        self.render_notices(clear=True)
        self.refresh_notices(force=True)

    def load_more_notices(self):
        owner, archived = self.qr_owner(), self._notice_archived
        cursor = getattr(self, '_notice_cursor', None)
        if not cursor:
            return
        def done(page):
            if self.qr_owner() == owner and self.active == 'Avisos' and self._notice_archived == archived:
                seen = {r['id'] for r in self._notice_rows}
                self._notice_rows.extend(r for r in page['threads'] if r['id'] not in seen)
                self._notice_cursor = page.get('next_cursor')
                self.render_notices(clear=True)
        self.network(lambda: QrInbox(self.cloud).list(archived, cursor), done)

    def open_qr_inbox(self, archived=False):
        self.remember_reply_draft()
        if self._notice_archived != archived:
            self._notice_rows, self._notice_cursor = [], None
        self._notice_archived = archived
        self.show('Avisos')
        self.refresh_notices(force=True)

    def qr_conversation_panel(self, result):
        self.remember_reply_draft()
        self._conversation_state = result
        self.show('Conversación')
        Clock.schedule_once(lambda _: setattr(self.scroll, 'scroll_y', 0), .1)

    def remember_reply_draft(self):
        if self.active != 'Conversación' or not self._conversation_state:
            return
        composer = next((w for w in self.content.children if 'message' in w.ids), None)
        if composer is None:
            return
        text, owner, thread = composer.ids.message.text, self.qr_owner(), self._conversation_state['id']
        draft = getattr(self, '_qr_reply_draft', None)
        if text.strip():
            request = draft['request'] if draft and draft['owner'] == owner and draft['thread'] == thread and draft['text'] == text else str(uuid4())
            self._qr_reply_draft = dict(owner=owner, thread=thread, text=text, request=request)
        else:
            self._qr_reply_draft = None

    def render_conversation(self):
        result = self._conversation_state
        if not result or not self.cloud.user:
            self.account()
            return
        self.content.add_widget(view('UxToolbar', title=result['pet_name'], left_icon='arrow-left',
            left=lambda *_: self.open_qr_inbox(), right_icon='dots-vertical',
            right=lambda *_: self.qr_conversation_options(result)))
        details = [result.get('finder_name'), result.get('location_note'), result.get('finder_contact')]
        if any(details):
            self.content.add_widget(view('UxCaption', text='\n'.join(value for value in details if value)))
        for message in result['messages']:
            date = datetime.fromisoformat(message['created_at']).astimezone().strftime('%d/%m · %H:%M')
            self.content.add_widget(view('QrInboxConversation', sender=message['sender'],
                label='Quien la encontró' if message['sender'] == 'visitor' else 'Tú', text=message['text'], date=date))
        if result.get('can_reply', True) and result['status'] in ('open', 'contacted'):
            draft = getattr(self, '_qr_reply_draft', None)
            value = draft['text'] if draft and draft['owner'] == self.qr_owner() and draft['thread'] == result['id'] else ''
            composer = view('UxComposer', value=value, callback=lambda *_: self.send_inline_reply(result['id'], composer))
            self.content.add_widget(composer)
        else:
            self.content.add_widget(view('UxCaption', text='Esta conversación está cerrada.'))

    def send_inline_reply(self, thread_id, composer):
        text = composer.ids.message.text.strip()
        if not text or self.busy:
            return
        if len(text) > 1000:
            self.message('Mensaje muy largo', 'Usa hasta 1000 caracteres.')
            return
        owner = self.qr_owner()
        draft = getattr(self, '_qr_reply_draft', None)
        request_id = draft['request'] if draft and draft['owner'] == owner and draft['thread'] == thread_id and draft['text'] == text else str(uuid4())
        self._qr_reply_draft = dict(owner=owner, thread=thread_id, text=text, request=request_id)
        def saved(result):
            if self.qr_owner() == owner:
                self._qr_reply_draft = None
                composer.ids.message.text = ''
                composer.ids.message.focus = False
                self.qr_conversation_panel(result)
        self.network(lambda: QrInbox(self.cloud).reply(thread_id, text, request_id), saved)

    def qr_page(self):
        self.heading('Su chapa QR', 'Una prueba de 14 días para una mascota')
        if not self.cloud.user:
            self.content.add_widget(view('UxCaption', text='Crea una cuenta o inicia sesión para probar la chapa de una mascota.'))
            self.content.add_widget(view('AccountPrimary', text='Crear cuenta o iniciar sesión', callback=self.account))
            return
        if not self.data['pets']:
            self.content.add_widget(view('AccountPrimary', text='Registrar mascota', callback=lambda *_: self.register_pet()))
            return
        owner = self.qr_owner()
        client = PublicChapas(self.cloud, self.cloud.site_url)
        def check():
            trial = client.trial_status()
            pet = next((p for p in self.data['pets'] if p['id'] == trial.get('pet_id')), None)
            return trial, pet, client.existing(pet['id']) if trial['used'] and pet else None
        def checked(result):
            if self.qr_owner() != owner or self.active != 'Chapa':
                return
            trial, pet, tag = result
            if trial['used'] and pet and tag:
                tag['access_kind'] = trial.get('access_kind', tag.get('access_kind', 'trial'))
                self.public_tag_panel(pet, tag)
                return
            self.content.clear_widgets()
            self.heading('Su chapa QR', 'Una prueba de 14 días para una mascota')
            if trial['used']:
                self.content.add_widget(view('UxCaption', text='Tu cuenta ya utilizó la prueba para ' + trial.get('pet_name', 'una mascota') + '. No se puede iniciar otra.'))
                if not pet:
                    self.content.add_widget(view('UxRow', title='Recuperar la mascota de mi cuenta', detail='Revisar la copia guardada',
                                                 icon='cloud-download-outline', callback=lambda *_: self.download()))
            else:
                self.content.add_widget(view('UxCaption', text='¿Para qué mascota quieres crear la chapa? La prueba incluye una sola.'))
                for item in self.data['pets']:
                    self.content.add_widget(view('UxRow', title=item['name'], detail='Elegir para la prueba', icon='qrcode', callback=lambda *_, p=item: self.public_tag_panel(p, None)))
        self.network(check, checked)

    def public_tag_panel(self, pet, tag):
        self.active, self.subtitle.text = 'Chapa', 'Chapa'
        self.content.clear_widgets()
        self.content.add_widget(view('UxToolbar', title=pet['name'], left_icon='refresh', left=lambda *_: self.show('Chapa'),
            right_icon='dots-vertical', right=lambda *_: self.public_tag_options(pet, tag)))
        if tag is None:
            self.heading('Prueba su chapa', '14 días · una mascota por cuenta')
            self.content.add_widget(view('UxCaption', text='El QR permitirá avisarte sin publicar tu teléfono. La prueba empieza al crear la chapa y no se renueva al borrar una mascota.'))
            self.content.add_widget(view('AccountPrimary', text='Crear chapa de prueba', callback=lambda *_: self.publish_public_tag(pet, 'issue')))
        elif tag['status'] == 'active':
            path = self.public_tag_path(pet)
            write_public_png(tag, path)
            self.content.add_widget(view('UxQr', source=str(path)))
            date = datetime.fromisoformat(tag['expires_at']).astimezone().strftime('%d/%m/%Y')
            paid = tag.get('access_kind') == 'paid'
            days = max(1, ceil((datetime.fromisoformat(tag['expires_at'])-datetime.now(timezone.utc)).total_seconds()/86400))
            label = 'Chapa activa · hasta el ' + date if paid else f'Prueba · quedan {days} días · hasta el {date}'
            self.content.add_widget(view('UxCaption', text=label))
            self.content.add_widget(view('AccountPrimary', text='Ver ficha web', callback=lambda *_: webbrowser.open(tag['url'])))
        else:
            self.heading('Ficha pausada' if tag['status'] == 'expired' else 'Chapa desactivada', '')
            text = 'Conserva tu chapa: al renovar el plan se reactivará el mismo QR.' if tag.get('access_kind') == 'paid' else 'La prueba de 14 días terminó. Tu QR se conserva; la suscripción aún está en preparación.'
            if tag['status'] == 'unavailable':
                text = 'Esta chapa está desactivada. Renovar el plan no cambia tu decisión de privacidad.'
            self.content.add_widget(view('UxCaption', text=text))
        self.scroll.scroll_y = 1

    def public_tag_options(self, pet, tag):
        modal, card = self.dialog('Opciones de la chapa', 440)
        def action(title, icon, callback):
            def run(*_):
                modal.dismiss()
                callback()
            card.add_widget(view('UxRow', title=title, detail='', icon=icon, callback=run))
        if tag and tag['status'] == 'active':
            action('Privacidad del contacto', 'shield-outline', partial(self.qr_contact_privacy, pet))
            action('Actualizar datos de la ficha', 'cloud-sync-outline', partial(self.publish_public_tag, pet, 'sync'))
            action('Desactivar chapa', 'cancel', partial(self.revoke_public_tag, pet))
        else:
            card.add_widget(view('UxCaption', text='La prueba incluye una sola chapa durante 14 días por cuenta.'))
        modal.open()

    def plan_info(self):
        modal, card = self.dialog('Chapa y suscripción', 460)
        card.add_widget(view('UxCaption', text='La chapa circular llevará el QR delante y el nombre de tu mascota detrás.'))
        card.add_widget(view('UxCaption', text='Al terminar el periodo pagado, la ficha se pausará. Al renovar, volverá a funcionar el mismo QR. Tus registros locales seguirán disponibles.'))
        card.add_widget(view('UxCaption', text='El plan incluirá cuidados compartidos y resumen de salud. Estamos probando estas funciones sin cobros; la suscripción y la chapa física todavía no están a la venta.'))
        modal.open()

    def open_care_sharing(self):
        if not self.require_account():
            return
        owner = self.qr_owner()
        def received(result):
            if self.qr_owner() == owner:
                self._shared_list = result['pets']
                self.show('Compartidos')
        self.network(lambda: CareShare(self.cloud).call('list'), received)

    def render_care_sharing(self):
        self.heading('Cuidados compartidos', 'Consulta sus rutinas e historial con alguien de confianza.')
        self.content.add_widget(view('UxRow', title='Tengo una invitación', detail='Usar el código que te compartieron', icon='ticket-outline', callback=lambda *_: self.join_care_share()))
        if self.data['pets']:
            self.content.add_widget(view('UxSection', text='Mis mascotas'))
            for pet in self.data['pets']:
                self.content.add_widget(view('UxRow', title=pet['name'], detail='Administrar personas invitadas', icon='paw', callback=lambda *_, p=pet: self.care_members(p)))
        rows = getattr(self, '_shared_list', [])
        if rows:
            self.content.add_widget(view('UxSection', text='Compartidas conmigo'))
            for pet in rows:
                self.content.add_widget(view('UxRow', title=pet['name'], detail=pet['kind'], icon='paw-outline', callback=lambda *_, p=pet: self.open_shared_pet(p['id'])))

    def join_care_share(self):
        def submit(values):
            try:
                code = CareShare.invite_code(values['code'])
            except CloudError as exc:
                return str(exc)
            owner = self.qr_owner()
            name = self.contact_profile().get('name') or 'Familiar'
            self.network(lambda: CareShare(self.cloud).join(code, name),
                         lambda _: self.open_care_sharing() if self.qr_owner() == owner else None)
        self.form('Aceptar invitación', [('code', 'Código de invitación', '')], submit, persist=False, submit_text='Aceptar',
                  description='Podrás consultar las rutinas y el historial de esa mascota. Su dueño puede retirar el acceso.')

    def care_members(self, pet):
        self.retry_backup()
        owner = self.qr_owner()
        def received(result):
            if self.qr_owner() != owner:
                return
            modal, outer = self.dialog('Personas invitadas', 550)
            modal.size_hint_y = .85
            scroll, card = view('AccountScroll'), view('QrInfoBody')
            scroll.add_widget(card)
            outer.add_widget(scroll)
            card.add_widget(view('UxCaption', text=pet['name']))
            card.add_widget(view('UxCaption', text='Pueden consultar sus rutinas y su historial. No ven tu teléfono ni otras mascotas.'))
            for member in result['members']:
                def remove(*_, m=member):
                    modal.dismiss()
                    self.confirm('Retirar acceso', '¿Retirar el acceso de ' + m['name'] + '?',
                                 lambda: self.network(lambda: CareShare(self.cloud).call('revoke', pet_id=pet['id'], id=m['id']), lambda _: self.care_members(pet)))
                card.add_widget(view('UxRow', title=member['name'], detail='Toca para retirar su acceso', icon='account-minus-outline', callback=remove))
            def invite(*_):
                modal.dismiss()
                self.confirm('Compartir cuidados', 'La persona invitada podrá consultar las rutinas y los registros de salud de ' + pet['name'] + '.',
                             lambda: self.create_care_invite(pet))
            if len(result['members']) < 3:
                card.add_widget(view('AccountPrimary', text='Invitar a una persona', callback=invite))
            else:
                card.add_widget(view('UxCaption', text='Puedes compartir con hasta 3 personas. Retira un acceso para invitar a alguien más.'))
            def cancel(*_):
                modal.dismiss()
                self.network(lambda: CareShare(self.cloud).call('cancel_invite', pet_id=pet['id']), lambda _: self.saved_feedback('Invitación cancelada'))
            card.add_widget(view('UxRow', title='Cancelar código pendiente', detail='', icon='ticket-outline', callback=cancel))
            modal.open()
        self.network(lambda: CareShare(self.cloud).call('members', pet_id=pet['id']), received)

    def create_care_invite(self, pet):
        self.retry_backup()
        owner = self.qr_owner()
        def received(result):
            if self.qr_owner() != owner:
                return
            modal, card = self.dialog('Invitación', 400)
            card.add_widget(view('UxCaption', text='Para ' + pet['name']))
            card.add_widget(view('UxCaption', text='Dale este código solo a la persona que quieres invitar. Vence en 48 horas y sirve una vez.'))
            from kivy.core.clipboard import Clipboard
            card.add_widget(view('UxCode', value=result['code']))
            def copy(*_):
                Clipboard.copy(result['code'])
                self.saved_feedback('Código copiado')
            card.add_widget(view('AccountPrimary', text='Copiar código', callback=copy))
            modal.open()
        self.network(lambda: CareShare(self.cloud).call('invite', pet_id=pet['id']), received)

    def open_shared_pet(self, membership):
        owner = self.qr_owner()
        def received(result):
            if self.qr_owner() == owner:
                self._shared_pet = result
                self.show('Cuidado compartido')
        self.network(lambda: CareShare(self.cloud).call('read', id=membership), received)

    def render_shared_pet(self):
        pet = getattr(self, '_shared_pet', None)
        if not pet or not self.cloud.user:
            self.show('Cuenta')
            return
        self.content.add_widget(view('UxToolbar', title=pet['name'], left_icon='arrow-left', left=lambda *_: self.open_care_sharing(),
                                     right_icon='refresh', right=lambda *_: self.open_shared_pet(pet['id'])))
        self.content.add_widget(view('UxCaption', text='Acceso de consulta. Los cambios se verán cuando su dueño los guarde en su cuenta.'))
        for key, title in [('routines', 'Rutinas'), ('events', 'Historial')]:
            self.content.add_widget(view('UxSection', text=title))
            entries = sorted(pet[key], key=lambda entry: entry.get('date') or entry.get('time') or '', reverse=True) if key == 'events' else pet[key]
            if not entries:
                self.content.add_widget(view('UxCaption', text='Sin registros todavía.'))
            for item in entries[:40]:
                stamp = item.get('date') or item.get('time') or ''
                status = ' · Completado' if item.get('done') else ''
                self.content.add_widget(view('QrInboxConversation', sender='owner', label=stamp + status, text=item['title']+'\n'+(item.get('detail') or ''), date=''))
            if len(entries) > 40:
                self.content.add_widget(view('UxCaption', text='Se muestran hasta 40 registros por sección.'))
        def leave(*_):
            self.confirm('Dejar de seguir', 'Dejarás de ver los cuidados de esta mascota.',
                         lambda: self.network(lambda: CareShare(self.cloud).call('leave', id=pet['id']), lambda _: self.open_care_sharing()))
        self.content.add_widget(view('UxRow', title='Dejar de seguir esta mascota', detail='', icon='account-minus-outline', callback=leave))

    def export_health_report(self):
        if not self.selected_pet:
            return
        self.confirm('Compartir resumen de salud', 'El PDF incluirá los registros de salud y cuidados de esta mascota. Compártelo solo con quien tú elijas.', self.prepare_health_report)

    def prepare_health_report(self):
        from services.health_report import create_health_report, share_health_report
        from kivy.utils import platform
        try:
            if platform == 'android':
                from jnius import autoclass
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                root = Path(str(activity.getCacheDir().getAbsolutePath()))
            else:
                from tempfile import gettempdir
                root = Path(gettempdir()) / 'mimascota'
        except Exception:
            self.message('No se pudo preparar el PDF', 'Inténtalo de nuevo al volver a abrir la app.')
            return
        from copy import deepcopy
        snapshot, pet_id = deepcopy(self.data), self.selected_pet
        owner, source = self.qr_owner(), self.data_file
        path = root / 'health-reports' / ('resumen-' + uuid4().hex + '.pdf')
        def ready(result):
            if self.qr_owner() != owner or self.data_file != source:
                result.unlink(missing_ok=True)
                return
            try:
                share_health_report(result)
            except Exception:
                self.message('No se pudo compartir el PDF', 'Inténtalo otra vez. Revisa que tengas una app para abrir o compartir PDF.')
        self.network(lambda: create_health_report(snapshot, pet_id, path), ready)
