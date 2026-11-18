from datetime import datetime
from pathlib import Path
import webbrowser
from screens.views import view, ViewColumn
from services.premium import PremiumState
from services.subscription import Subscription


class BillingFeatures:
    def premium_card(self):
        pets = self.data['pets']
        pet = next((p for p in pets if p['id'] == self.selected_pet), pets[0] if pets else None)
        return view('PremiumTeaser', name=pet['name'] if pet else 'Tu mascota',
                    active=self.premium_state().active(pet['id']) if pet else False,
                    source=self.premium_image(), callback=lambda *_: self.plan_info())

    def premium_image(self):
        return str(Path(__file__).resolve().parents[1] / 'assets/chapa-personalizable.png')

    def premium_state(self):
        owner = self.cloud.user['id'] if self.cloud.user else None
        key = (owner, str(self.data_file))
        if getattr(self, '_premium_key', None) != key:
            self._premium_key = key
            self._premium_state = PremiumState(self.data_file.with_suffix('.premium.json'), owner)
        return self._premium_state

    def update_premium_badge(self):
        state = self.premium_state()
        state.retain_pets(p['id'] for p in self.data['pets'])
        self.shell.ids.account.premium = state.active()
        self.shell.ids.account.icon = 'account-star-outline' if state.active() else 'account-outline'

    def start_premium_status(self):
        from kivy.clock import Clock
        previous = getattr(self, '_premium_clock', None)
        if previous:
            previous.cancel()
        self._premium_refresh_token = None
        self._premium_renewals = {}
        self._premium_last_refresh = None
        self.update_premium_badge()
        self._premium_clock = Clock.schedule_interval(self.refresh_premium_badge, 60)
        Clock.schedule_once(lambda _: self.refresh_premium_badge(force=True), .3)

    def refresh_premium_badge(self, *_, force=False):
        from kivy.clock import Clock
        from threading import Thread
        from time import monotonic
        self.update_premium_badge()
        if (not getattr(self, '_premium_motion_active', True) or not self.cloud.user
                or not self.cloud.configured or getattr(self, '_premium_refresh_token', None)):
            return
        last = getattr(self, '_premium_last_refresh', None)
        if not force and last is not None and monotonic() - last < 60:
            return
        owner, source = self.cloud.user['id'], self.data_file
        pets = list(self.data['pets'])
        if not pets:
            return
        token = object()
        self._premium_refresh_token = token
        self._premium_last_refresh = monotonic()
        def run():
            results = []
            for pet in pets:
                try:
                    results.append((pet['id'], Subscription(self.cloud).call(pet['id'])))
                except Exception:
                    pass  # El distintivo es opcional; no bloquea el cuidado sin conexión.
            def done(_):
                if self._premium_refresh_token is not token:
                    return
                self._premium_refresh_token = None
                if not self.cloud.user or self.cloud.user['id'] != owner or self.data_file != source:
                    return
                current = {p['id'] for p in self.data['pets']}
                for pet_id, result in results:
                    if pet_id in current:
                        self.premium_state().record(pet_id, result, acknowledge=False)
                self.update_premium_badge()
            Clock.schedule_once(done)
        Thread(target=run, daemon=True).start()

    def set_premium_motion(self, enabled):
        self._premium_motion_active = bool(enabled)
        self.shell.ids.account.motion_active = enabled
        welcome = getattr(self, '_premium_welcome', None)
        if welcome:
            welcome.motion_active = enabled and getattr(self, '_billing_modal', None) is not None and self._billing_modal._is_open

    def stop_premium_status(self):
        self._premium_refresh_token = None
        timer = getattr(self, '_premium_clock', None)
        if timer:
            timer.cancel()
        self.set_premium_motion(False)

    def accept_premium_result(self, pet, result):
        # Un resultado anterior no debe reemplazar la confirmación recién recibida.
        self._premium_refresh_token = None
        fresh = self.premium_state().record(pet['id'], result)
        self.update_premium_badge()
        if fresh:
            self.payment_success(pet, result)
        else:
            self.render_subscription(pet, result)

    def payment_success(self, pet, result):
        previous = getattr(self, '_billing_modal', None)
        if previous:
            previous.dismiss()
        modal, card = self.dialog('Pago confirmado', 630)
        modal.size_hint_y = .86
        scroll, content = view('AccountScroll'), ViewColumn(adaptive=True)
        end = datetime.fromisoformat(result['paid_until']).astimezone().strftime('%d/%m/%Y')
        renewal = getattr(self, '_premium_renewals', {}).pop(pet['id'], False)
        welcome = view('PremiumWelcome', name=pet['name'], kind=pet.get('kind', ''),
                       breed=pet.get('breed', ''), date=end, renewal=renewal)
        self._premium_welcome = welcome
        content.add_widget(welcome)
        content.add_widget(view('AccountNote', text='Pago de prueba confirmado.'))
        scroll.add_widget(content)
        card.add_widget(scroll)
        owner, source = self.cloud.user['id'], self.data_file
        self._billing_modal, self._billing_pet, self._billing_owner = modal, None, owner
        def enjoy(*_):
            modal.dismiss()
            if self.cloud.user and self.cloud.user['id'] == owner and self.data_file == source:
                self.selected_pet = pet['id']
                self.show('Chapa')
        card.add_widget(view('AccountPrimary', text='Ver su chapa', callback=enjoy))
        def closed(*_):
            welcome.motion_active = False
            if self._premium_welcome is welcome:
                self._premium_welcome = None
            self.measurement_screen(self.active)
        modal.bind(on_dismiss=closed)
        from kivy.clock import Clock
        from kivy.core.window import Window
        def fit_success(*_):
            fixed = sum(child.height for child in card.children if child is not scroll)
            wanted = content.minimum_height + fixed + card.padding[1] + card.padding[3] + card.spacing * (len(card.children) - 1)
            modal.size_hint_y = min(.88, wanted / Window.height)
        resize = Clock.create_trigger(fit_success, 0)
        content.bind(minimum_height=resize)
        modal.bind(size=resize, on_open=resize)
        modal.open()
        self.measurement_screen('Premium')

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
        source = self.data_file
        def received(result):
            if self.cloud.user and self.cloud.user['id'] == owner and self.data_file == source:
                self.accept_premium_result(pet, result)
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
        card.add_widget(view('PremiumBenefit', icon='tag-heart-outline', text='Chapa física incluida en la primera compra'))
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
        if state in ('none', 'active', 'rejected', 'cancelled', 'expired'):
            def signup(*_):
                def submit():
                    if not self.cloud.user or self.cloud.user['id'] != owner:
                        return
                    if not hasattr(self, '_premium_renewals'):
                        self._premium_renewals = {}
                    self._premium_renewals[pet['id']] = self.premium_state().active(pet['id'])
                    self.network(lambda: Subscription(self.cloud).call(pet['id'], 'create'), created)
                def created(data):
                    if not self.cloud.user or self.cloud.user['id'] != owner:
                        return
                    self.accept_premium_result(pet, data)
                    if data.get('checkout_url'):
                        webbrowser.open(data['checkout_url'])
                self.confirm('Pago de prueba',
                    '$3.990 CLP por un mes para ' + pet['name'] + '. Renovación manual. '
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
