"""Centro de avisos QR. No modifica ni programa los recordatorios de cuidados."""
from datetime import datetime
from pathlib import Path
from threading import Thread
from uuid import uuid4
from kivy.clock import Clock
from kivy.lang import Builder
from screens.views import view
from services.cloud import CloudError
from services.qr_inbox import QrInbox

_loaded = False


class QrInboxFeatures:
    def start_qr_inbox(self):
        global _loaded
        if not _loaded:
            Builder.load_file(str(Path(__file__).with_suffix('.kv')))
            _loaded = True
        self._qr_unread = 0
        self._qr_owner = None
        self._qr_fetching = False
        self._qr_modal = None
        self._qr_poll = Clock.schedule_interval(self.refresh_qr_badge, 30)
        Clock.schedule_once(self.refresh_qr_badge, 1)

    def qr_owner(self):
        return (self.cloud.user or {}).get('id')

    def refresh_qr_badge(self, *_):
        owner = self.qr_owner()
        if owner != self._qr_owner:
            self._qr_owner, self._qr_unread = owner, 0
            self._qr_reply_draft = None
            self._notice_rows, self._notice_cursor = [], None
            self._conversation_state = None
            self._shared_list, self._shared_pet = [], None
            if self._qr_modal:
                self._qr_modal.dismiss()
                self._qr_modal = None
            self.set_qr_badge()
        if not owner or self._qr_fetching or self.busy or getattr(self, '_reminder_running', False):
            return
        self._qr_fetching = True
        def run():
            try:
                result = QrInbox(self.cloud).list()
            except CloudError:
                result = None
            def done(_):
                self._qr_fetching = False
                if self.qr_owner() == owner and result is not None:
                    self._qr_unread = result['unread']
                    self.set_qr_badge()
            Clock.schedule_once(done)
        Thread(target=run, daemon=True).start()

    def set_qr_badge(self):
        # One bell retains its existing care reminder action through the center.
        self.shell.ids.notifications.icon = 'bell-badge-outline' if self._qr_unread else 'bell-outline'
        self.shell.ids.qr_unread_badge.text = str(min(99, self._qr_unread)) if self._qr_unread else ''
        self.shell.ids.qr_unread_badge.opacity = 1 if self._qr_unread else 0

    def notifications_center(self, *_):
        self.refresh_qr_badge()
        modal, card = self.dialog('Tus avisos', 380)
        card.add_widget(view('AccountNote', text='Los mensajes QR quedan guardados en tu cuenta aunque borres una notificación del teléfono.'))
        def open_view(callback):
            modal.dismiss()
            callback()
        count = f' · {self._qr_unread} sin leer' if self._qr_unread else ''
        card.add_widget(view('AccountAction', text='Mensajes de tus mascotas' + count,
                             callback=lambda *_: open_view(self.open_qr_inbox)))
        card.add_widget(view('AccountAction', text='Recordatorios de cuidados',
                             callback=lambda *_: open_view(self.notifications)))
        modal.open()

    def open_qr_inbox(self, archived=False):
        if self.busy or not self.require_account():
            return
        owner = self.qr_owner()
        def show(result):
            if self.qr_owner() == owner:
                self.qr_inbox_panel(result, archived)
        self.network(lambda: QrInbox(self.cloud).list(archived), show)

    def qr_inbox_panel(self, result, archived=False):
        modal, card = self.dialog('Mensajes archivados' if archived else 'Avisos de tus mascotas', 650)
        modal.size_hint_y = .9
        self._qr_modal = modal
        self._qr_unread = result['unread']
        self.set_qr_badge()
        scroll, body = view('AccountScroll'), view('QrInfoBody')
        body.add_widget(view('QrInboxText', text='Los avisos se conservan 30 días. Abre una conversación para leerla y responder.'))
        rows = [row for row in result['threads'] if row['archived'] == archived]
        if not rows:
            body.add_widget(view('QrInboxText', text='No hay conversaciones aquí todavía.'))
        for row in rows:
            count = f" · {row['unread']} sin leer" if row['unread'] else ''
            body.add_widget(view('QrInboxEntry', text=row['pet_name'] + count,
                                 callback=lambda *_, item=row: self.open_qr_conversation(item['id'], modal)))
            body.add_widget(view('QrInboxText', text=row['preview'][:160]))
        cursor = result.get('next_cursor')
        if cursor:
            owner = self.qr_owner()
            def more(*_):
                modal.dismiss()
                def append(page):
                    if self.qr_owner() != owner:
                        return
                    seen = {row['id'] for row in result['threads']}
                    page['threads'] = result['threads'] + [row for row in page['threads'] if row['id'] not in seen]
                    self.qr_inbox_panel(page, archived)
                self.network(lambda: QrInbox(self.cloud).list(archived, cursor), append)
            body.add_widget(view('AccountAction', text='Mostrar avisos anteriores', callback=more))
        def action(callback):
            modal.dismiss()
            callback()
        body.add_widget(view('AccountAction', text='Actualizar', callback=lambda *_: action(lambda: self.open_qr_inbox(archived))))
        body.add_widget(view('AccountAction', text='Ver activos' if archived else 'Ver archivados',
                             callback=lambda *_: action(lambda: self.open_qr_inbox(not archived))))
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()

    def open_qr_conversation(self, thread_id, previous=None):
        if previous:
            previous.dismiss()
        if self.busy or not self.require_account():
            return
        owner = self.qr_owner()
        def received(result):
            if self.qr_owner() != owner:
                return
            self.qr_conversation_panel(result)
            # Only acknowledge a rendered message, never the newest row blindly.
            last = result['messages'][-1]['id'] if result['messages'] else None
            if last:
                def acknowledge():
                    try:
                        if self.qr_owner() == owner:
                            QrInbox(self.cloud).mark_read(thread_id, last)
                    except CloudError:
                        pass  # An acknowledgement failure leaves messages unread.
                    Clock.schedule_once(self.refresh_qr_badge)
                Clock.schedule_once(lambda _: Thread(target=acknowledge, daemon=True).start(), .2)
        self.network(lambda: QrInbox(self.cloud).read(thread_id), received)

    def qr_conversation_panel(self, result):
        modal, card = self.dialog('Aviso de ' + result['pet_name'], 690)
        modal.size_hint_y = .92
        self._qr_modal = modal
        scroll, body = view('AccountScroll'), view('QrInfoBody')
        for key, label in [('finder_name', 'Persona'), ('location_note', 'Dónde está'), ('finder_contact', 'Contacto voluntario')]:
            if result[key]:
                body.add_widget(view('QrInboxText', text=label + ': ' + result[key]))
        for message in result['messages']:
            stamp = datetime.fromisoformat(message['created_at']).astimezone().strftime('%d/%m %H:%M')
            body.add_widget(view('QrInboxConversation', sender=message['sender'], label='Quien la encontró' if message['sender'] == 'visitor' else 'Tú',
                                 text=message['text'], date=stamp))
        labels = dict(open='Abierta', contacted='Ya contactaste', resolved='Mascota encontrada', blocked='Conversación bloqueada')
        body.add_widget(view('QrInboxText', text=labels[result['status']]))
        def action(callback):
            modal.dismiss()
            callback()
        if result.get('can_reply', True) and result['status'] in ('open', 'contacted'):
            body.add_widget(view('AccountPrimary', text='Responder', callback=lambda *_: action(lambda: self.reply_qr_message(result['id']))))
        body.add_widget(view('AccountAction', text='Actualizar mensajes', callback=lambda *_: action(lambda: self.open_qr_conversation(result['id']))))
        body.add_widget(view('AccountAction', text='Opciones', callback=lambda *_: action(lambda: self.qr_conversation_options(result))))
        body.add_widget(view('AccountAction', text='Volver a la bandeja', callback=lambda *_: action(self.open_qr_inbox)))
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()
        Clock.schedule_once(lambda _: (body.do_layout(), scroll.update_from_scroll(), setattr(scroll, 'scroll_y', 0)), 0)

    def reply_qr_message(self, thread_id):
        owner = self.qr_owner()
        previous = getattr(self, '_qr_reply_draft', None)
        draft = previous if previous and previous['owner'] == owner and previous['thread'] == thread_id else None
        def submit(values):
            if self.qr_owner() != owner:
                return
            message = values['detail'].strip()
            if not message or len(message) > 1000:
                return 'Escribe un mensaje de hasta 1000 caracteres.'
            request_id = draft['request'] if draft and draft['text'] == message else str(uuid4())
            self._qr_reply_draft = dict(owner=owner, thread=thread_id, text=message, request=request_id)
            def saved(result):
                if self.qr_owner() == owner:
                    self._qr_reply_draft = None
                    self.qr_conversation_panel(result)
            self.network(lambda: QrInbox(self.cloud).reply(thread_id, message, request_id), saved)
        self.form('Responder al aviso', [('detail', 'Mensaje', draft['text'] if draft else '')], submit, persist=False,
                  submit_text='Enviar mensaje', description='La persona leerá la respuesta en su enlace privado. No hace falta compartir tu teléfono.')

    def qr_conversation_options(self, result):
        if hasattr(self, 'remember_reply_draft'):
            self.remember_reply_draft()
        modal, card = self.dialog('Opciones del aviso', 520)
        def run(operation):
            modal.dismiss()
            self.network(operation, lambda _: self.open_qr_conversation(result['id']))
        inbox = QrInbox(self.cloud)
        card.add_widget(view('AccountAction', text='Actualizar mensajes',
                             callback=lambda *_: (modal.dismiss(), self.open_qr_conversation(result['id']))))
        if result['status'] in ('open', 'contacted'):
            card.add_widget(view('AccountAction', text='Ya contacté', callback=lambda *_: run(lambda: inbox.status(result['id'], 'contacted'))))
            card.add_widget(view('AccountAction', text='Mascota encontrada', callback=lambda *_: run(lambda: inbox.status(result['id'], 'resolved'))))
        card.add_widget(view('AccountAction', text='Sacar del archivo' if result['archived'] else 'Archivar conversación',
                             callback=lambda *_: run(lambda: inbox.archive(result['id'], not result['archived']))))
        def block(*_):
            modal.dismiss()
            self.confirm('Bloquear conversación', 'Esta persona no podrá enviar más mensajes en esta conversación.',
                         lambda: self.network(lambda: inbox.status(result['id'], 'blocked'), self.qr_conversation_panel))
        if result['status'] != 'blocked':
            card.add_widget(view('AccountAction', text='Bloquear', callback=block))
        card.add_widget(view('AccountNote', text='Archivar no borra los mensajes ni los marca como leídos.'))
        modal.open()

    def qr_contact_privacy(self, pet):
        if not self.require_account():
            return
        modal, card = self.dialog('Privacidad de la chapa', 540)
        card.add_widget(view('AccountNote', text='El contacto protegido permite recibir y responder avisos sin publicar tu teléfono.'))
        def set_mode(mode, confirmed=False):
            modal.dismiss()
            self.network(lambda: QrInbox(self.cloud).mode(pet['id'], mode, confirmed),
                         lambda _: self.message('Privacidad actualizada', 'La opción se guardó en el servidor. El plazo de la chapa no cambió.'))
        card.add_widget(view('AccountPrimary', text='Contacto protegido', callback=lambda *_: set_mode('protected')))
        def show_phone(*_):
            modal.dismiss()
            self.confirm('¿Publicar tu teléfono?', 'Quien tenga el enlace podrá copiarlo o guardarlo. Primero debes haber elegido y autorizado un contacto para esta mascota y guardado los cambios en la nube.',
                         lambda: self.network(lambda: QrInbox(self.cloud).mode(pet['id'], 'phone', True),
                                              lambda _: self.message('Teléfono publicado', 'La ficha mostrará el contacto autorizado. Puedes volver al modo protegido desde estas opciones.')))
        card.add_widget(view('AccountAction', text='Mostrar teléfono autorizado', callback=show_phone))
        card.add_widget(view('AccountAction', text='Desactivar el contacto', callback=lambda *_: set_mode('disabled')))
        card.add_widget(view('AccountNote', text='Estas opciones no renuevan los 14 días. Desactivar el contacto impide nuevos avisos; los ya guardados permanecen en tu bandeja.'))
        modal.open()
