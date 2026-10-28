"""Pantalla de chapa web: publicación explícita y fechas verificadas por servidor."""
from copy import deepcopy
from datetime import datetime
from functools import partial
import webbrowser

from kivy.clock import Clock
from screens.views import view
from services.public_qr import PublicChapas, write_public_png


class PublicTagFeatures:
    def public_tag_path(self, pet):
        return self.data_file.parent / 'qr' / self.data_file.stem / ('web-' + pet['id'] + '.png')

    def open_public_tag(self, pet):
        if self.busy or not self.require_account():
            return
        try:
            client = PublicChapas(self.cloud, self.cloud.site_url)
        except ValueError as exc:
            self.message("URL de chapa pendiente", str(exc))
            return
        self.network(lambda: client.existing(pet["id"]),
                     lambda tag: self.public_tag_panel(pet, tag))

    def public_tag_panel(self, pet, tag):
        modal, card = self.dialog("Chapa de " + pet["name"], 690)
        modal.size_hint_y = .92
        scroll = view('QrInfoScroll')
        body = view('QrInfoBody')
        body.add_widget(view('AccountNote', text='Un escaneo para ayudarle a volver a casa.'))
        contact = pet.get('qr_contact', {})
        shared = isinstance(contact, dict) and contact.get('share_phone') is True
        body.add_widget(view('AccountNote', text=(
            'Contacto guardado: ' + contact.get('name', '') + ' · ' + contact.get('phone', '')
            if shared else 'Puedes recibir avisos sin publicar un teléfono.')))

        def action(label, callback, primary=False):
            def run(*_):
                if self.busy:
                    return
                modal.dismiss()
                callback()
            body.add_widget(view('AccountPrimary' if primary else 'AccountAction', text=label, callback=run))

        if tag is None:
            body.add_widget(view('AccountNote', text='Crea su QR y prueba la ficha durante 14 días.'))
            action('Crear QR', partial(self.publish_public_tag, pet, 'issue'), primary=True)
        elif tag['status'] == 'active':
            expires = datetime.fromisoformat(tag['expires_at']).astimezone()
            body.add_widget(view('AccountSection', text='CHAPA ACTIVA'))
            path = self.public_tag_path(pet)
            write_public_png(tag, path)
            frame = view('QrInfoQrFrame', source=str(path))
            frame.children[0].reload()
            body.add_widget(frame)
            body.add_widget(view('AccountNote', text='Vence el ' + expires.strftime('%d/%m/%Y %H:%M')
                                 + '.'))
            action('Ver ficha', lambda: webbrowser.open(tag['url']), primary=True)
        else:
            body.add_widget(view('AccountSection', text=(
                'PRUEBA FINALIZADA' if tag['status'] == 'expired' else 'CHAPA DESACTIVADA')))
            body.add_widget(view('AccountNote', text='La ficha ya no muestra mascota ni contacto. '
                                 'Esta prueba no puede reiniciarse.'))
            try:
                self.public_tag_path(pet).unlink(missing_ok=True)
            except OSError:
                pass
        if tag is None or tag['status'] == 'active':
            action('Editar contacto', partial(self.qr_contact_form, pet))
        action('Más opciones', partial(self.public_tag_options, pet, tag))
        if tag and tag['status'] == 'active':
            action('Privacidad del contacto', partial(self.qr_contact_privacy, pet))
        scroll.add_widget(body)
        card.add_widget(scroll)
        modal.open()
        Clock.schedule_once(lambda _: (body.do_layout(), scroll.update_from_scroll()), 0)

    def public_tag_options(self, pet, tag):
        modal, card = self.dialog('Opciones de la chapa', 440)
        card.children[-1].size_hint_y = None
        def action(label, callback):
            def run(*_):
                if self.busy:
                    return
                modal.dismiss()
                callback()
            card.add_widget(view('AccountAction', text=label, callback=run))
        if tag and tag['status'] == 'active':
            action('Actualizar ficha', partial(self.publish_public_tag, pet, 'sync'))
            action('Desactivar chapa', partial(self.revoke_public_tag, pet))
        action('Sobre la privacidad', lambda: self.message('Tú eliges qué compartir',
               'La ficha muestra nombre y especie. El contacto se incluye solo si lo autorizas. '
               'Para publicar cambios, usa Actualizar ficha. Desactivar la chapa oculta sus datos; '
               'no puede borrar información que alguien ya haya leído o guardado.'))
        action('Prueba de texto sin conexión', lambda: self.qr_info(pet, local=True))
        modal.open()

    def publish_public_tag(self, pet, action):
        if self.busy or not self.require_account():
            return
        if not 1 <= len(pet.get('name', '').strip()) <= 48 or not 1 <= len(pet.get('kind', '').strip()) <= 32:
            self.message('Revisa el perfil', 'Para la ficha web usa un nombre de hasta 48 caracteres '
                         'y una especie de hasta 32 caracteres.')
            return
        try:
            client = PublicChapas(self.cloud, self.cloud.site_url)
        except ValueError as exc:
            self.message('URL de chapa pendiente', str(exc))
            return
        contact = pet.get('qr_contact', {})
        shared = isinstance(contact, dict) and contact.get('share_phone') is True
        contact_text = 'Una chapa de prueba para ' + pet['name'] + ', durante 14 días por cuenta.'
        def publish():
            from services.backup_sync import synchronize, SyncJournal
            def prepare():
                # network serializes this operation with the background worker.
                journal = SyncJournal(self.data_file)
                return synchronize(self.cloud, deepcopy(self.data), journal.base)
            def uploaded(result):
                merged, revision = result
                self.data.update(merged)
                self.data['cloud_revision'] = revision
                if self.save():
                    SyncJournal(self.data_file).accept(merged)
                    self.network(lambda: client.manage(pet['id'], action),
                                 lambda tag: self.public_tag_panel(pet, tag))
            self.network(prepare, uploaded)
        self.confirm('Crear QR' if action == 'issue' else 'Actualizar ficha',
                       contact_text + ('\nLa prueba empieza hoy y no se reinicia al borrar la mascota.'
                       if action == 'issue' else '\nSe guardarán tus cambios. La fecha de vencimiento no cambia.'), publish)

    def revoke_public_tag(self, pet):
        if self.busy or not self.require_account():
            return
        def revoke():
            client = PublicChapas(self.cloud, self.cloud.site_url)
            self.network(lambda: client.manage(pet['id'], 'revoke'),
                         lambda tag: self.public_tag_panel(pet, tag))
        self.confirm('Desactivar chapa', 'El QR dejará de mostrar mascota y contacto. '
                     'Una ficha abierta puede tardar hasta 30 segundos en actualizarse. '
                     'Esta prueba no podrá reactivarse.', revoke)
