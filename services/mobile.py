"""Adaptador Android opcional. No inicia SDK ni recopila datos sin configuración y elección."""
from kivy.utils import platform


class MobileServices:
    def __init__(self, config):
        self.config = config.get('FIREBASE_ANDROID', {})
        self.enabled = config.get('FIREBASE_ENABLED') is True
        self.bridge = None

    @property
    def configured(self):
        return (platform == 'android' and self.enabled and isinstance(self.config, dict)
                and all(isinstance(self.config.get(key), str) and self.config[key]
                        for key in ('app_id', 'api_key', 'project_id', 'sender_id')))

    def native(self):
        from jnius import autoclass
        return autoclass('org.mimascota.FirebaseBridge'), autoclass('org.kivy.android.PythonActivity').mActivity

    def preferences(self):
        if not self.configured:
            return dict(notifications=False, analytics=False)
        bridge, activity = self.native()
        return {key: bool(bridge.allowed(activity, key)) for key in ('notifications', 'analytics')}

    def initialize(self):
        bridge, activity = self.native()
        if self.bridge is None:
            bridge.initialize(activity, self.config['app_id'], self.config['api_key'],
                              self.config['project_id'], self.config['sender_id'])
            self.bridge = bridge
        return bridge

    def configure(self, notifications, analytics):
        if not self.configured:
            return
        bridge = self.initialize()
        bridge.analytics(bool(analytics))
        if notifications:
            from android.permissions import request_permissions
            from jnius import autoclass
            if autoclass('android.os.Build$VERSION').SDK_INT >= 33:
                request_permissions(['android.permission.POST_NOTIFICATIONS'],
                                    lambda _permissions, grants: bridge.notifications(bool(grants) and all(grants)))
            else:
                bridge.notifications(True)
        else:
            bridge.notifications(False)

    def screen(self, name):
        if self.configured and self.preferences()['analytics']:
            self.initialize().screen(name)
