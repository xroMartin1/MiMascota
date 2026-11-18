"""Offline end-to-end Premium presentation and account-isolation checks."""
import os
os.environ['MIMASCOTA_DISABLE_SAVED_SESSION'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from main import MiMascotaApp
from screens.premium import PersonalTag, PremiumAccountButton, PremiumWelcome
from screens.views import ViewAction, ViewText
from services.cloud import CloudError
from services.store import empty_data, pet_values


class Check(MiMascotaApp):
    def build(self):
        self.temp = TemporaryDirectory()
        self.cloud = Mock(user=None, configured=False, config={}, site_url='https://example.invalid')
        self.cloud.request.side_effect = CloudError('Offline UI fixture')
        with patch('screens.home.DATA_FILE', Path(self.temp.name)/'guest.json'), patch(
                'screens.home.Supabase', return_value=self.cloud):
            return super().build()

    def on_start(self):
        super().on_start()
        self.s = self.root.get_screen('home')
        self.browser = patch('screens.billing.webbrowser.open')
        self.browser_mock = self.browser.start()
        self.out = Path('previews/premium-experience')
        self.out.mkdir(parents=True, exist_ok=True)
        self.steps = self.scenarios()
        Window.minimum_height = 400
        Clock.schedule_once(self.advance, .5)

    def advance(self, *_):
        try:
            next(self.steps)
        except StopIteration:
            self.browser_mock.assert_not_called()
            self.browser.stop()
            self.stop()
            self.temp.cleanup()
            print('PASS: Premium 390/320/480, real names and breeds, visible CTA/scroll, '
                  'fresh orders once, cache restart, renewal, failed payments retain badge, '
                  'pause/resume, reduced motion, dismiss and account isolation')
            return
        Clock.schedule_once(self.advance, .35)

    @staticmethod
    def labels(widget):
        return [w.text for w in widget.walk() if isinstance(w, ViewText)]

    def dismiss(self):
        modal = getattr(self.s, '_billing_modal', None)
        if modal and modal._is_open:
            modal.dismiss(animation=False)

    def check_modal(self, welcome=False):
        modal = self.s._billing_modal
        assert modal._is_open and modal.height < Window.height
        labels = self.labels(modal)
        assert not any(term in text.casefold() for text in labels for term in
                       ('luna', 'referencia de pago', 'order-', '11111111-', 'no incluida', 'checkout='))
        footer = next(w for w in modal.ids.card.children if isinstance(w, ViewAction))
        assert modal.y <= footer.y and footer.top <= modal.top, (footer.pos, modal.pos)
        assert footer.height >= 40
        welcomes = [w for w in modal.walk() if isinstance(w, PremiumWelcome)]
        assert bool(welcomes) == welcome
        if welcome:
            assert len(welcomes) == 1
            assert sum(isinstance(w, PremiumWelcome) for surface in Window.children for w in surface.walk()) == 1
            assert footer.text == 'Ver su chapa'
            avatar = next(w for w in welcomes[0].walk() if w.__class__.__name__ == 'ViewPetAvatar')
            assert Path(avatar.portrait_source).stem == self.pet['breed'].casefold()
        else:
            tag = next(w for w in modal.walk() if isinstance(w, PersonalTag))
            assert tag.name == self.pet['name']
            assert tag._name_size[0] <= min(tag.size)*.59+1
        return modal

    def scenarios(self):
        s = self.s
        self.cloud.user = {'id': 'premium-owner-a', 'email': 'fixture@example.invalid', 'user_metadata': {}}
        s.switch_store(Path(self.temp.name)/'account-a.json')
        s.mobile = Mock(configured=False)
        s.data = empty_data()
        for ident, name, kind, breed in (('cat', 'Jurel', 'Gato', 'Ragdoll'),
                                        ('dog', 'María José de los Ángeles Ñandú', 'Perro', 'Beagle')):
            s.data['pets'].append(dict(pet_values(dict(name=name, kind=kind, breed=breed, age='3', weight='5')), id=ident))
        s.store.save(s.data)
        s.selected_pet = 'cat'
        self.pet = s.data['pets'][0]
        badge = s.shell.ids.account
        assert isinstance(badge, PremiumAccountButton) and not badge.premium
        for width, height in ((390,844),(320,640),(320,480)):
            Window.size = width, height
            s.show('Cuenta')
            yield
            assert '$3.990 CLP / mes' in self.labels(s.content)
            tag = next(w for w in s.content.walk() if isinstance(w, PersonalTag))
            assert tag.name == 'Jurel'
            self.root.export_to_png(str(self.out/f'perfil-{width}x{height}.png'))
            s.render_subscription(self.pet, dict(state='none', order_id='order-secret-11111111-hidden'))
            yield
            self.check_modal().export_to_png(str(self.out/f'detalle-{width}x{height}.png'))
            self.dismiss()
        expiry = datetime.now(timezone.utc)+timedelta(days=30)
        result = dict(state='active', order_id='order-first-cat', paid_until=expiry.isoformat())
        s.set_premium_motion(False)
        assert s.premium_state().record(self.pet['id'], result, acknowledge=False)
        assert result['order_id'] not in s.premium_state().seen
        assert self.on_pause()
        self.on_resume()
        yield
        assert result['order_id'] not in s.premium_state().seen
        assert not getattr(s, '_premium_welcome', None)
        Window.size = 390,844
        s.accept_premium_result(self.pet, result)
        yield
        modal = self.check_modal(welcome=True)
        welcome = s._premium_welcome
        assert badge.premium
        s.set_premium_motion(True)
        start_phase = badge._phase
        modal.export_to_png(str(self.out/'bienvenida-jurel-390.png'))
        yield
        assert badge._ring_event is not None and badge._phase != start_phase
        assert self.on_pause()
        assert badge._ring_event is None and welcome.phase == 1
        self.on_resume()
        yield
        assert badge._ring_event is not None
        s.set_premium_motion(False)
        assert badge._ring_event is None and welcome.phase == 1
        self.dismiss()
        assert not any(a.have_properties_to_animate(welcome) for a in Animation._instances)
        s.set_premium_motion(True)
        s.show('Cuenta')
        yield
        self.root.export_to_png(str(self.out/'perfil-premium-390.png'))
        with patch.object(s, 'payment_success', wraps=s.payment_success) as success:
            s.accept_premium_result(self.pet, result)
            success.assert_not_called()
            self.dismiss()
            s._premium_key = None
            s.accept_premium_result(self.pet, result)
            success.assert_not_called()
            self.dismiss()
        with patch.object(s, 'motion_enabled', return_value=False):
            s.set_premium_motion(True)
            yield
            assert badge._ring_event is None
            self.root.export_to_png(str(self.out/'perfil-movimiento-reducido-390.png'))
        s._premium_renewals = {self.pet['id']: True}
        renewed = dict(result, order_id='order-renewal-cat', paid_until=(expiry+timedelta(days=30)).isoformat())
        Window.size = 320,480
        s.accept_premium_result(self.pet, renewed)
        yield
        modal = self.check_modal(welcome=True)
        assert '¡Premium renovado!' in self.labels(modal)
        modal.export_to_png(str(self.out/'renovacion-jurel-320x480.png'))
        scroll = next(w for w in modal.walk() if w.__class__.__name__ == 'AccountScroll')
        assert scroll.children[0].height > scroll.height
        scroll.scroll_y = 0
        yield
        modal.export_to_png(str(self.out/'renovacion-abajo-320x480.png'))
        self.dismiss()
        with patch.object(s, 'payment_success', wraps=s.payment_success) as success:
            s.accept_premium_result(self.pet, renewed)
            success.assert_not_called()
            self.dismiss()
            for state in ('pending', 'rejected'):
                s.accept_premium_result(self.pet, dict(state=state, order_id='order-failed'))
                assert badge.premium and s.premium_state().active(self.pet['id'])
                success.assert_not_called()
                self.dismiss()
        self.pet = s.data['pets'][1]
        s.selected_pet = self.pet['id']
        s.render_subscription(self.pet, dict(state='none'))
        yield
        self.check_modal().export_to_png(str(self.out/'nombre-largo-320x480.png'))
        self.dismiss()
        s.accept_premium_result(self.pet, dict(result, order_id='order-first-dog'))
        yield
        self.check_modal(welcome=True).export_to_png(str(self.out/'bienvenida-beagle-320x480.png'))
        self.dismiss()
        self.cloud.user = {'id': 'premium-owner-b', 'email': 'other@example.invalid', 'user_metadata': {}}
        s.switch_store(Path(self.temp.name)/'account-b.json')
        assert not badge.premium and badge._ring_event is None
        self.cloud.user = {'id': 'premium-owner-a', 'email': 'fixture@example.invalid', 'user_metadata': {}}
        s.switch_store(Path(self.temp.name)/'account-a.json')
        assert badge.premium
        self.cloud.logout.side_effect = lambda: setattr(self.cloud, 'user', None)
        with patch('screens.features.PushClient'), patch.object(s, 'network', side_effect=lambda op, done: done(op())):
            s.logout()
        assert self.cloud.user is None and not badge.premium and badge._ring_event is None
        self.root.export_to_png(str(self.out/'sesion-cerrada-320x480.png'))
        yield


if __name__ == '__main__':
    Check().run()
