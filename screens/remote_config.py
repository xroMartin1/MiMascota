"""Non-blocking refresh; updates just the tip, without resetting the scroll."""
from threading import Thread
from time import monotonic
from kivy.clock import Clock
from screens.views import view
from services.remote_config import RemoteConfig


class RemoteConfigFeatures:
    def start_remote_config(self):
        self.remote_config = RemoteConfig(self.cloud, self.guest_file.parent / 'remote-config.json')
        self._tip_running = False
        self._tip_last_attempt = None
        Clock.schedule_once(self.refresh_care_tip, .6)

    def care_tip(self):
        self._tip_view = view('HomeCareTip', message=self.remote_config.message,
                              status=self.remote_config.status)
        return self._tip_view

    def refresh_care_tip(self, *_):
        now = monotonic()
        if self._tip_running or (self._tip_last_attempt is not None and now - self._tip_last_attempt < 60):
            return
        self._tip_running = True
        self._tip_last_attempt = now

        def run():
            try:
                self.remote_config.refresh()
            finally:
                Clock.schedule_once(done)

        def done(_):
            self._tip_running = False
            card = getattr(self, '_tip_view', None)
            if card is not None and card.parent is not None:
                card.ids.tip_text.text = self.remote_config.message
                card.ids.tip_status.text = self.remote_config.status

        Thread(target=run, daemon=True).start()
