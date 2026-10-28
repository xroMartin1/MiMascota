"""Controlador de navegación y diálogos; diseños declarativos en home.kv."""
from copy import deepcopy
from functools import partial
from pathlib import Path
from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from screens.features import CareFeatures
from screens.views import load_views, view
from services.store import LocalStore
from services.cloud import Supabase
from services.google_auth import GoogleAuth
from services.mobile import MobileServices
from screens.qr_inbox import QrInboxFeatures
from screens.ux import UxFeatures
from screens.sync import BackupFeatures
from screens.remote_config import RemoteConfigFeatures

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "petcare.json"


class HomeScreen(RemoteConfigFeatures, BackupFeatures, UxFeatures, QrInboxFeatures, CareFeatures, MDScreen):
    def __init__(self, data_file=None, **kwargs):
        load_views()
        super().__init__(**kwargs)
        if data_file is None:
            data_file = (Path(App.get_running_app().user_data_dir) / "petcare.json"
                         if platform in ("android", "ios") else DATA_FILE)
        self.guest_file = Path(data_file)
        self.data_file = self.guest_file
        self.store = LocalStore(self.data_file)
        self.data = deepcopy(self.store.data)
        self.cloud = Supabase()
        self.google_auth = GoogleAuth(self.cloud)
        self.mobile = MobileServices(self.cloud.config)
        if platform == 'android':
            from android import activity
            activity.bind(on_new_intent=self.google_intent)
        self.busy = False
        self.notified = set()
        self.active = "Inicio"
        self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
        self.shell = view('HomeShell', notifications=self.notifications_center, account=self.account,
                          brand_logo=str(Path(__file__).resolve().parents[1] / 'assets/brand/logo-negativo.png'))
        self.header = self.shell.ids.header
        self.subtitle = self.shell.ids.subtitle
        self.scroll = self.shell.ids.scroll
        self.content = self.shell.ids.content
        self.nav = self.shell.ids.navigation
        self.add_widget(self.shell)
        self.shell.size = self.size
        self.bind(size=self.shell.setter('size'))
        self.start_qr_inbox()
        self.start_backup()
        self.start_ux()
        self.start_remote_config()
        self.show("Inicio")
        self.reminder_clock = Clock.schedule_interval(self.check_reminders, 30)
        self.push_sync_clock = Clock.schedule_interval(self.retry_reminders, 30)
        if platform == "android":
            from jnius import autoclass
            intent = autoclass("org.kivy.android.PythonActivity").mActivity.getIntent()
            if self.google_auth.pending:
                Clock.schedule_once(lambda _: self.google_intent(intent), .8)
        if self.store.readonly:
            Clock.schedule_once(lambda _: self.message("Archivo protegido", "No se pudo leer el archivo local. No se sobrescribirá. Revisa data/petcare.json y su copia .bak."), .5)


    def show(self, page, *_):
        changing_page = self.active != page
        Animation.cancel_all(self.content, 'opacity')
        self.content.opacity = 1
        self.active = page
        try:
            self.mobile.screen(page)
        except Exception:
            pass  # La telemetría opcional nunca bloquea el cuidado local.
        self.content.spacing = dp(14)
        self.subtitle.text = page
        self.content.clear_widgets()
        self.nav.clear_widgets()
        for title, icon in [("Inicio", "home-outline"), ("Mascotas", "paw"),
                            ("Chapa", "qrcode-scan"), ("Rutina", "creation"),
                            ("Salud", "heart-pulse")]:
            if title == "Chapa":
                self.nav.add_widget(view('NavigationQr', text=title, icon=icon, callback=partial(self.show, 'Chapa'), selected=page == 'Chapa'))
            else:
                self.nav.add_widget(view(
                    'NavigationTab',
                    text=title,
                    icon=icon,
                    selected=title == page,
                    callback=partial(self.show, title),
                ))
        {"Inicio": self.home, "Mascotas": self.pets, "Rutina": self.routine, "Salud": self.health,
         "Avisos": self.render_notices, "Cuenta": self.render_account, "Chapa": self.qr_page,
         "Conversación": self.render_conversation, "Compartidos": self.render_care_sharing,
         "Cuidado compartido": self.render_shared_pet}[page]()
        self.scroll.scroll_y = 1
        if changing_page and self.motion_enabled():
            self.content.opacity = .82
            Animation(opacity=1, duration=.26, t='out_sine').start(self.content)

    def motion_enabled(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                settings = autoclass('android.provider.Settings$Global')
                return settings.getFloat(activity.getContentResolver(),
                                         'animator_duration_scale', 1.0) > 0
            except Exception:
                pass
        return True


    def heading(self, title, subtitle, badge=None):
        box = view('HeadingBox')
        if badge:
            line = view('HeadingLine')
            tag = view('HeadingTag', text=badge)
            tag.size_hint_x = .78
            line.add_widget(tag)
            line.add_widget(view('HeadingSpacer'))
            box.add_widget(line)
        box.add_widget(view('HeadingTitle', text=title))
        if subtitle:
            box.add_widget(view('HeadingSubtitle', text=subtitle))
        self.content.add_widget(box)


    def detail_row(self, icon, title, detail, warm=False):
        line = view('DetailRowLine', icon=icon, warm=warm, title=title, detail=detail)
        return line


    def link_card(self, icon, title, detail, page, warm=False):
        card = view('LinkCard')
        line = view('LinkCardLine')
        line.add_widget(self.detail_row(icon, title, detail, warm))
        line.add_widget(view('LinkArrow', callback=partial(self.show, page)))
        card.add_widget(line)
        return card


    def select_pet(self, pet_id, *_):
        self.selected_pet = pet_id
        self.show("Salud")


    def dialog(self, title, height=360):
        modal = view('CareDialog', height=height, text=title, callback=lambda *_: modal.dismiss())
        card = modal.ids.card
        return modal, card

    def saved_feedback(self, text):
        previous = getattr(self, '_feedback', None)
        timer = getattr(self, '_feedback_timer', None)
        if timer:
            timer.cancel()
        if previous and previous.parent:
            Animation.cancel_all(previous)
            self.remove_widget(previous)
        feedback = view('SavedFeedback', text=text)
        self._feedback = feedback
        self.add_widget(feedback)
        animated = self.motion_enabled()
        if animated:
            feedback.opacity = 0
            Animation(opacity=1, duration=.18, t='out_sine').start(feedback)
        def remove(*_):
            if feedback.parent:
                self.remove_widget(feedback)
        def hide(_):
            if animated:
                fade = Animation(opacity=0, duration=.22, t='in_sine')
                fade.bind(on_complete=remove)
                fade.start(feedback)
            else:
                remove()
        self._feedback_timer = Clock.schedule_once(hide, 2)


    def message(self, title, body):
        modal, card = self.dialog(title, 330)
        card.add_widget(view('MessageBody', text=body))
        card.add_widget(view('MessageAccept', callback=lambda *_: modal.dismiss()))
        modal.open()
