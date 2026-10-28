"""Bandeja QR autenticada. Los mensajes se guardan en el servidor, no en petcare.json."""
from datetime import datetime
from uuid import UUID, uuid4
from services.cloud import CloudError


def identifier(value):
    try:
        return isinstance(value, str) and UUID(value).version == 4
    except (ValueError, TypeError, AttributeError):
        return False


def text(value, maximum, required=False):
    return (isinstance(value, str) and len(value) <= maximum and
            (not required or bool(value.strip())) and
            all(ord(c) >= 32 or c in '\n\r\t' for c in value))


def timestamp(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value).tzinfo is not None
    except (ValueError, TypeError):
        return False


class QrInbox:
    def __init__(self, cloud):
        self.cloud = cloud

    def call(self, action, **values):
        if not self.cloud.user:
            raise CloudError('Inicia sesión para consultar los avisos de tus mascotas.')
        try:
            return self.cloud.request('POST', '/functions/v1/qr-inbox',
                                      dict(action=action, **values), authorized=True)
        except CloudError:
            raise CloudError('No pudimos completar el aviso. Revisa la conexión y que la chapa '
                             'o la conversación sigan activas. Tus mensajes guardados se conservan.') from None

    def list(self, archived=False, cursor=None):
        if type(archived) is not bool or (cursor is not None and (
                not isinstance(cursor, dict) or not identifier(cursor.get('id')) or not timestamp(cursor.get('at')))):
            raise CloudError('Página de bandeja inválida.')
        raw = self.call('list', archived=archived, **({'cursor': cursor} if cursor else {}))
        if (not isinstance(raw, dict) or type(raw.get('unread')) is not int or raw['unread'] < 0
                or not isinstance(raw.get('threads'), list) or len(raw['threads']) > 50):
            raise CloudError('No pudimos leer la bandeja. Inténtalo de nuevo.')
        rows = []
        for row in raw['threads']:
            if (not isinstance(row, dict) or not identifier(row.get('id')) or
                    row.get('status') not in ('open', 'contacted', 'resolved', 'blocked') or
                    type(row.get('archived')) is not bool or type(row.get('unread')) is not int or row['unread'] < 0 or
                    not timestamp(row.get('updated_at')) or not text(row.get('pet_name'), 48, True) or
                    not text(row.get('pet_id'), 64, True) or not text(row.get('preview'), 1000, True)):
                raise CloudError('No pudimos leer la bandeja. Inténtalo de nuevo.')
            rows.append({key: row[key] for key in ('id', 'pet_id', 'pet_name', 'status', 'archived', 'unread', 'updated_at', 'preview')})
        next_cursor = raw.get('next_cursor')
        if next_cursor is not None and (not isinstance(next_cursor, dict) or
                not identifier(next_cursor.get('id')) or not timestamp(next_cursor.get('at'))):
            raise CloudError('No pudimos leer la página siguiente.')
        return dict(unread=raw['unread'], threads=rows, next_cursor=next_cursor)

    @staticmethod
    def conversation(raw):
        if (not isinstance(raw, dict) or not identifier(raw.get('id')) or
                raw.get('status') not in ('open', 'contacted', 'resolved', 'blocked') or
                type(raw.get('archived')) is not bool or not timestamp(raw.get('expires_at')) or
                (raw.get('owner_read_at') is not None and not timestamp(raw['owner_read_at'])) or
                not isinstance(raw.get('messages'), list) or len(raw['messages']) > 60 or
                not text(raw.get('pet_name'), 48, True) or not text(raw.get('pet_id'), 64, True) or
                not text(raw.get('finder_name'), 60) or not text(raw.get('finder_contact'), 120) or
                not text(raw.get('location_note'), 200)):
            raise CloudError('No pudimos leer la conversación. Inténtalo de nuevo.')
        messages = []
        for message in raw['messages']:
            if (not isinstance(message, dict) or not identifier(message.get('id')) or
                    message.get('sender') not in ('visitor', 'owner') or
                    not text(message.get('text'), 1000, True) or not timestamp(message.get('created_at'))):
                raise CloudError('No pudimos leer la conversación. Inténtalo de nuevo.')
            messages.append({key: message[key] for key in ('id', 'sender', 'text', 'created_at')})
        result = {key: raw[key] for key in ('id', 'status', 'archived', 'expires_at', 'owner_read_at',
                                          'pet_id', 'pet_name', 'finder_name', 'finder_contact', 'location_note')}
        result['messages'] = messages
        result['can_reply'] = raw.get('can_reply', True) is True
        return result

    def read(self, thread_id):
        if not identifier(thread_id):
            raise CloudError('Conversación inválida.')
        return self.conversation(self.call('read', thread_id=thread_id))

    def mark_read(self, thread_id, message_id):
        if not identifier(thread_id) or not identifier(message_id):
            raise CloudError('Conversación inválida.')
        return self.conversation(self.call('mark_read', thread_id=thread_id, message_id=message_id))

    def reply(self, thread_id, message, request_id=None):
        if not identifier(thread_id) or not text(message, 1000, True):
            raise CloudError('Escribe un mensaje de hasta 1000 caracteres.')
        request_id = request_id or str(uuid4())
        if not identifier(request_id):
            raise CloudError('Solicitud inválida.')
        return self.conversation(self.call('reply', thread_id=thread_id, text=message.strip(), request_id=request_id))

    def status(self, thread_id, status):
        if not identifier(thread_id) or status not in ('open', 'contacted', 'resolved', 'blocked'):
            raise CloudError('Estado inválido.')
        return self.conversation(self.call('status', thread_id=thread_id, status=status))

    def archive(self, thread_id, archived=True):
        if not identifier(thread_id) or type(archived) is not bool:
            raise CloudError('Conversación inválida.')
        return self.conversation(self.call('archive', thread_id=thread_id, archived=archived))

    def mode(self, pet_id, mode, confirm_phone=False):
        if not text(pet_id, 64, True) or mode not in ('protected', 'phone', 'disabled'):
            raise CloudError('Opción de privacidad inválida.')
        if mode == 'phone' and confirm_phone is not True:
            raise CloudError('Confirma que quieres publicar tu teléfono.')
        raw = self.call('mode', pet_id=pet_id, mode=mode, confirm_phone=confirm_phone)
        if not isinstance(raw, dict) or raw.get('mode') != mode:
            raise CloudError('No pudimos confirmar el cambio de privacidad.')
        return raw
