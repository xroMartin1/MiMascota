"""Checkout Webpay de prueba alojado; solo el servidor concede Premium."""
from datetime import datetime
import re
from urllib.parse import parse_qsl, urlparse
from services.cloud import CloudError


class Subscription:
    def __init__(self, cloud):
        self.cloud = cloud

    def call(self, pet_id, action='status'):
        if not self.cloud.user:
            raise CloudError('Inicia sesión para consultar tu plan.')
        if action not in ('status', 'create') or not isinstance(pet_id, str) or not pet_id.strip():
            raise ValueError('Selecciona una mascota y una operación válida.')
        result = self.cloud.request('POST', '/functions/v1/webpay-payments',
                                   {'action': action, 'pet_id': pet_id}, authorized=True)
        if (not isinstance(result, dict) or result.get('provider') != 'webpay'
                or result.get('test_mode') is not True or type(result.get('amount')) is not int
                or result['amount'] != 3990 or result.get('currency') != 'CLP'):
            raise CloudError('No pudimos verificar el plan de prueba.')
        if result.get('state') not in ('none', 'creating', 'pending', 'active', 'rejected', 'cancelled', 'expired'):
            raise CloudError('No pudimos verificar el estado del pago.')
        if result.get('checkout_url') is not None:
            self.validate_checkout(result['checkout_url'])
        if result.get('paid_until') is not None:
            try:
                if datetime.fromisoformat(result['paid_until']).tzinfo is None:
                    raise ValueError
            except (ValueError, TypeError):
                raise CloudError('No pudimos verificar la vigencia del plan.') from None
        order = result.get('order_id')
        if order is not None and (not isinstance(order, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', order)):
            raise CloudError('No pudimos verificar la referencia del pago.')
        return result

    def validate_checkout(self, value):
        try:
            if not isinstance(value, str) or any(c.isspace() for c in value):
                raise ValueError
            url = urlparse(value)
            origin = urlparse(self.cloud.site_url)
            if (origin.scheme != 'https' or not origin.hostname or origin.port or origin.username or origin.password
                    or origin.path not in ('', '/') or origin.query or origin.fragment
                    or url.scheme != 'https' or url.hostname != origin.hostname or url.port
                    or url.netloc.lower() != origin.netloc.lower() or url.username or url.password
                    or url.path != '/pago/webpay' or url.fragment):
                raise ValueError
            query = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
            if (len(query) != 1 or query[0][0] != 'checkout'
                    or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[0-9a-f]{64}', query[0][1])):
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise CloudError('El enlace de pago no es válido.') from None
        return value
