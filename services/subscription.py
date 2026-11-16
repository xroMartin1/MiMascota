"""Checkout de prueba alojado; el cliente nunca concede acceso premium."""
from datetime import datetime
from urllib.parse import urlparse
from services.cloud import CloudError


class Subscription:
    def __init__(self, cloud):
        self.cloud = cloud

    def call(self, pet_id, action='status', payer_email=None):
        if not self.cloud.user:
            raise CloudError('Inicia sesión para consultar tu suscripción.')
        if action not in ('status','create','cancel') or not isinstance(pet_id,str) or not pet_id:
            raise ValueError('Selecciona una mascota.')
        payload={'action':action,'pet_id':pet_id}
        if action=='create':
            email=(payer_email or '').strip()
            if email.count('@')!=1 or any(c.isspace() for c in email) or '.' not in email.split('@')[-1]:
                raise ValueError('Escribe el correo del comprador de prueba de Mercado Pago.')
            payload['payer_email']=email
        result=self.cloud.request('POST','/functions/v1/subscription-payments',payload,authorized=True)
        if not isinstance(result,dict) or result.get('test_mode') is not True or result.get('amount')!=3990 or result.get('currency')!='CLP':
            raise CloudError('No pudimos verificar el plan de prueba.')
        if result.get('state') not in ('none','creating','pending','authorized','active','paused','cancelled'):
            raise CloudError('No pudimos verificar el estado de la suscripción.')
        if result.get('checkout_url'):
            url=urlparse(result['checkout_url'])
            if (url.scheme!='https' or url.hostname not in ('www.mercadopago.cl','www.mercadopago.com','www.mercadopago.com.ar')
                    or url.username or url.password or url.port or url.path!='/subscriptions/checkout'):
                raise CloudError('El enlace de pago no es válido.')
        if result.get('paid_until'):
            try:
                if datetime.fromisoformat(result['paid_until']).tzinfo is None:raise ValueError
            except (ValueError,TypeError):
                raise CloudError('No pudimos verificar la vigencia del plan.') from None
        return result
