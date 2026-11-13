from datetime import datetime
import webbrowser
from screens.views import view, ViewColumn
from services.subscription import Subscription


class BillingFeatures:
    def plan_info(self):
        if not self.require_account():return
        pets=self.data['pets']
        if not pets:
            self.prompt_register_pet('Elegir su suscripción')
            return
        options={f"{i+1}. {pet['name']}":pet for i,pet in enumerate(pets)}
        if len(options)==1:
            self.open_subscription(next(iter(options.values())))
        else:
            self.form('Elige su plan',[('pet','Mascota',next(iter(options)))],
                      lambda values:self.open_subscription(options[values['pet']]),
                      choices={'pet':tuple(options)},persist=False,submit_text='Ver suscripción')

    def open_subscription(self,pet):
        owner=self.cloud.user['id']
        def received(result):
            if self.cloud.user and self.cloud.user['id']==owner:self.render_subscription(pet,result)
        self.network(lambda:Subscription(self.cloud).call(pet['id']),received)

    def render_subscription(self,pet,result):
        previous=getattr(self,'_billing_modal',None)
        if previous:previous.dismiss()
        modal,container=self.dialog('Su plan Premium',650)
        modal.size_hint_y=.88
        scroll=view('AccountScroll')
        card=ViewColumn(adaptive=True)
        scroll.add_widget(card)
        container.add_widget(scroll)
        owner=self.cloud.user['id']
        self._billing_modal=modal
        self._billing_pet=pet
        self._billing_owner=owner
        def closed(*_):
            if self._billing_modal is modal:self._billing_pet=None
        modal.bind(on_dismiss=closed)
        card.add_widget(view('UxCaption',text=f"Para {pet['name']} · $3.990 CLP al mes"))
        card.add_widget(view('UxCaption',text='Entorno de prueba. Usa únicamente el comprador y la tarjeta de prueba de Mercado Pago.'))
        card.add_widget(view('UxCaption',text='Mantiene vigente la ficha de esta mascota con el mismo QR. La chapa física no está incluida.'))
        labels={'none':'Aún no tienes una suscripción. Activa primero su chapa de prueba.',
                'creating':'La creación está sin confirmar. No vuelvas a pagar; necesitamos revisar la solicitud.',
                'pending':'Falta completar el checkout o confirmar el pago.',
                'authorized':'Suscripción autorizada. Aún no hay un cobro aprobado confirmado.',
                'active':'Pago de prueba aprobado. Su ficha tiene un periodo premium.',
                'paused':'La suscripción está pausada.',
                'cancelled':'Renovación cancelada. No se solicitarán nuevos cobros de esta suscripción.'}
        card.add_widget(view('UxCaption',text=labels[result['state']]))
        if result.get('paid_until'):
            end=datetime.fromisoformat(result['paid_until']).astimezone().strftime('%d/%m/%Y')
            card.add_widget(view('UxCaption',text='Periodo confirmado hasta '+end))
        if result['state'] in ('none','cancelled'):
            def signup(*_):
                modal.dismiss()
                def submit(values):
                    self.network(lambda:Subscription(self.cloud).call(pet['id'],'create',values['email']),created)
                def created(data):
                    if not self.cloud.user or self.cloud.user['id']!=owner:return
                    self.render_subscription(pet,data)
                    if data.get('checkout_url'):webbrowser.open(data['checkout_url'])
                self.form('Pagar en modo de prueba',[('email','Correo del comprador de prueba','')],submit,
                          persist=False,submit_text='Ir a Mercado Pago',
                          description='$3.990 CLP al mes. Escribe el correo de la cuenta ficticia de comprador, no tu contraseña. No se guardan datos de tarjeta en Mi Mascota.')
            card.add_widget(view('AccountPrimary',text='Suscribirme en modo de prueba',callback=signup))
        elif result.get('checkout_url'):
            card.add_widget(view('AccountPrimary',text='Continuar en Mercado Pago',callback=lambda *_:webbrowser.open(result['checkout_url'])))
        card.add_widget(view('AccountAction',text='Comprobar pago',callback=lambda *_:self.open_subscription(pet)))
        if result['state'] in ('pending','authorized','active','paused'):
            def cancel(*_):
                modal.dismiss()
                self.confirm('Cancelar renovación','Se cancelan los futuros cobros de prueba. Se conserva el periodo ya confirmado.',
                             lambda:self.network(lambda:Subscription(self.cloud).call(pet['id'],'cancel'),lambda data:self.render_subscription(pet,data) if self.cloud.user and self.cloud.user['id']==owner else None))
            card.add_widget(view('AccountAction',text='Cancelar renovación',callback=cancel))
        modal.open()

    def refresh_subscription(self,*_):
        pet=getattr(self,'_billing_pet',None)
        if pet and self.cloud.user and self.cloud.user['id']==getattr(self,'_billing_owner',None) and not self.busy:self.open_subscription(pet)
