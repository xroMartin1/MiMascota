from datetime import datetime
from pathlib import Path
import webbrowser
from screens.views import view, ViewColumn
from services.subscription import Subscription


class BillingFeatures:
    def premium_card(self):
        return view('PremiumTeaser', source=self.premium_image(), callback=lambda *_: self.plan_info())

    def premium_image(self):
        return str(Path(__file__).resolve().parents[1] / 'assets/chapa-premium.png')

    def plan_info(self, pet=None):
        if not self.require_account():
            return
        pets = self.data['pets']
        if not pets:
            self.prompt_register_pet('Elegir Premium')
        elif pet is not None:
            self.open_subscription(pet)
        elif len(pets) == 1:
            self.open_subscription(pets[0])
        else:
            modal, card = self.dialog('Premium para tu mascota', 480)
            scroll, entries = view('AccountScroll'), ViewColumn(adaptive=True)
            for item in pets:
                def choose(*_, selected=item):
                    modal.dismiss()
                    self.open_subscription(selected)
                entries.add_widget(view('HealthPetOption', name=item['name'], kind=item['kind'], breed=item['breed'],
                    detail=item['breed'], selected=False, callback=choose))
            scroll.add_widget(entries)
            card.add_widget(scroll)
            modal.size_hint_y = .8
            modal.open()

    def open_subscription(self, pet):
        owner = self.cloud.user['id']
        def received(result):
            if self.cloud.user and self.cloud.user['id'] == owner:
                self.render_subscription(pet, result)
        self.network(lambda: Subscription(self.cloud).call(pet['id']), received)

    def render_subscription(self, pet, result):
        previous = getattr(self, '_billing_modal', None)
        if previous:
            previous.dismiss()
        modal, container = self.dialog('Mi Mascota Premium', 650)
        modal.size_hint_y = .88
        scroll, card = view('AccountScroll'), ViewColumn(adaptive=True)
        scroll.add_widget(card)
        container.add_widget(scroll)
        owner = self.cloud.user['id']
        self._billing_modal, self._billing_pet, self._billing_owner = modal, pet, owner
        def closed(*_):
            if self._billing_modal is modal:
                self._billing_pet = None
            from kivy.clock import Clock
            def restore_screen(_):
                current = getattr(self, '_billing_modal', None)
                if not current or not current._is_open:
                    self.measurement_screen(self.active)
            Clock.schedule_once(restore_screen, .1)
        modal.bind(on_dismiss=closed)
        card.add_widget(view('PremiumHero', name=pet['name'], source=self.premium_image()))
        card.add_widget(view('PremiumPrice'))
        card.add_widget(view('PremiumBenefit', icon='web', text='Su ficha sigue disponible'))
        card.add_widget(view('PremiumBenefit', icon='qrcode', text='Conserva el mismo QR'))
        state = result['state']
        labels = {
            'none': ('Sin Premium', 'Un pago habilita un mes. La renovación es manual.'),
            'creating': ('Estamos comprobando tu solicitud', 'Actualiza el estado antes de intentar otro pago.'),
            'pending': ('Pago pendiente', 'Completa el pago de prueba en Webpay y vuelve para comprobarlo.'),
            'active': ('Premium activo', 'Puedes renovar manualmente y conservar el tiempo ya pagado.'),
            'rejected': ('Pago rechazado', 'No se activó un nuevo periodo. Puedes intentar otro pago.'),
            'cancelled': ('Pago anulado', 'No se activó un nuevo periodo. Puedes intentar otro pago.'),
            'expired': ('Pago vencido', 'El plazo terminó. Puedes intentar otro pago.'),
        }
        title, detail = labels[state]
        if result.get('paid_until'):
            end = datetime.fromisoformat(result['paid_until']).astimezone().strftime('%d/%m/%Y')
            detail = (detail + '\n' if detail else '') + 'Disponible hasta el ' + end
        card.add_widget(view('PremiumStatus', title=title, detail=detail,
                             bg='#E2F0EA' if state == 'active' else '#F4F8F8'))
        refresh = lambda *_: self.open_subscription(pet)
        if result.get('order_id'):
            card.add_widget(view('PremiumStatus', title='Referencia de pago',
                                 detail=result['order_id'], bg='#F4F8F8'))
        if state in ('none', 'active', 'rejected', 'cancelled', 'expired'):
            def signup(*_):
                def submit():
                    if not self.cloud.user or self.cloud.user['id'] != owner:
                        return
                    self.network(lambda: Subscription(self.cloud).call(pet['id'], 'create'), created)
                def created(data):
                    if not self.cloud.user or self.cloud.user['id'] != owner:
                        return
                    self.render_subscription(pet, data)
                    if data.get('checkout_url'):
                        webbrowser.open(data['checkout_url'])
                self.confirm('Pago de prueba',
                    '$3.990 CLP por un mes por mascota. Renovación manual. '
                    'Webpay está en modo de prueba: usa solo tarjetas de prueba, nunca tarjetas reales.', submit)
            container.add_widget(view('AccountPrimary',
                text='Renovar Premium' if state == 'active' else 'Pagar con Webpay', callback=signup))
            card.add_widget(view('AccountAction', text='Actualizar estado', callback=refresh))
        elif state == 'pending' and result.get('checkout_url'):
            container.add_widget(view('AccountPrimary', text='Continuar con Webpay',
                callback=lambda *_: self.continue_checkout(result['checkout_url'], owner)))
            card.add_widget(view('AccountAction', text='Actualizar estado', callback=refresh))
        else:
            container.add_widget(view('AccountPrimary', text='Actualizar estado', callback=refresh))
        modal.open()
        self.measurement_screen('Premium')

    def continue_checkout(self, url, owner=None):
        def open_checkout():
            if not self.cloud.user or (owner is not None and self.cloud.user['id'] != owner):
                return
            webbrowser.open(Subscription(self.cloud).validate_checkout(url))
        self.confirm('Pago de prueba',
            'Webpay está en modo de prueba: usa solo tarjetas de prueba, nunca tarjetas reales.', open_checkout)

    def refresh_subscription(self, *_):
        pet = getattr(self, '_billing_pet', None)
        if pet and self.cloud.user and self.cloud.user['id'] == getattr(self, '_billing_owner', None) and not self.busy:
            self.open_subscription(pet)
