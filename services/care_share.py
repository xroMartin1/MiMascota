"""Explicit read-only access to one pet. Never downloads an owner's full backup."""
from uuid import UUID
from services.cloud import CloudError


class CareShare:
    def __init__(self, cloud):
        self.cloud = cloud

    def call(self, action, **payload):
        result = self.cloud.request('POST', '/functions/v1/care-share', dict(action=action, **payload), authorized=True)
        if not isinstance(result, dict):
            raise CloudError('No pudimos abrir los cuidados compartidos.')
        return result

    @staticmethod
    def invite_code(code):
        try:
            value = UUID(code.strip())
            if value.version != 4:
                raise ValueError
        except (ValueError, AttributeError):
            raise CloudError('Revisa el código de invitación.') from None
        return str(value)

    def join(self, code, name):
        return self.call('join', code=self.invite_code(code), name=(name.strip() or 'Familiar')[:60])
