"""Controlador de navegación y diálogos; diseños declarativos en home.kv."""
from copy import deepcopy
from functools import partial
from pathlib import Path
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from screens.features import CareFeatures
from screens.views import load_views, view
from services.store import LocalStore
from services.cloud import Supabase

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "petcare.json"


class HomeScreen(CareFeatures, MDScreen):
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
        self.busy = False
        self.notified = set()
        self.active = "Inicio"
        self.selected_pet = self.data["pets"][0]["id"] if self.data["pets"] else None
        self.shell = view('HomeShell', notifications=self.notifications, account=self.account)
        self.header = self.shell.ids.header
        self.subtitle = self.shell.ids.subtitle
        self.scroll = self.shell.ids.scroll
        self.content = self.shell.ids.content
        self.nav = self.shell.ids.navigation
        self.add_widget(self.shell)
        # Mantener la vista al tamaño real del Screen incluso cuando KivyMD
        # omite el primer pase de layout del gestor de pantallas.
        self.bind(size=self.shell.setter("size"))
        self.bind(size=lambda *_: self.shell.do_layout())
        self.show("Inicio")
        self.reminder_clock = Clock.schedule_interval(self.check_reminders, 30)
        if self.store.readonly:
            Clock.schedule_once(lambda _: self.message("Archivo protegido", "No se pudo leer el archivo local. No se sobrescribirá. Revisa data/petcare.json y su copia .bak."), .5)


    def show(self, page, *_):
        self.active = page
        self.content.spacing = dp(10 if page == "Inicio" else 14)
        self.subtitle.text = page
        self.content.clear_widgets()
        self.nav.clear_widgets()
        for title, icon in [("Inicio", "home-outline"), ("Mascotas", "paw"),
                            ("Chapa", "qrcode-scan"), ("Rutina", "creation"),
                            ("Salud", "heart-pulse")]:
            if title == "Chapa":
                self.nav.add_widget(view('NavigationQr', text=title, icon=icon, callback=self.qr_info))
            else:
                self.nav.add_widget(view(
                    'NavigationTab',
                    text=title,
                    icon=icon,
                    selected=title == page,
                    callback=partial(self.show, title),
                ))
        {"Inicio": self.home, "Mascotas": self.pets, "Rutina": self.routine, "Salud": self.health}[page]()
        self.scroll.scroll_y = 1


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


    def message(self, title, body):
        modal, card = self.dialog(title, 330)
        card.add_widget(view('MessageBody', text=body))
        card.add_widget(view('MessageAccept', callback=lambda *_: modal.dismiss()))
        modal.open()
