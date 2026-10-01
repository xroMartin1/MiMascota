"""Shell y componentes de las pantallas; flujos funcionales en features.py."""
from copy import deepcopy
from functools import partial
from pathlib import Path
from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex, platform
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivymd.uix.screen import MDScreen
from screens.widgets import Card, Action, Text, row, column, pill, icon_tile, PRIMARY, INK, MUTED, MINT, PEACH, WHITE, LIME
from screens.features import CareFeatures
from services.store import LocalStore
from services.cloud import Supabase

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "petcare.json"


class HomeScreen(CareFeatures, MDScreen):
    def __init__(self, data_file=None, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#FFFFFF")
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
        self.shell = column(spacing=0)
        self.add_widget(self.shell)
        self.header = Card(bg="#FFFFFF", radius=0, orientation="horizontal", adaptive=False,
                           size_hint_y=None, height=dp(72), padding=[dp(18), dp(10)], spacing=10)
        self.header.add_widget(icon_tile("paw", size=40, bg=LIME))
        branding = column(spacing=0, size_hint_y=None, height=dp(46), pos_hint={"center_y": .5})
        branding.add_widget(Text("Mi Mascota", 22, INK, bold=True, height=28))
        self.subtitle = Text("Inicio", 11, MUTED, height=18)
        branding.add_widget(self.subtitle)
        self.header.add_widget(branding)
        header_actions = row(height=40, spacing=8, size_hint_x=None, width=dp(88),
                             pos_hint={"center_y": .5})
        header_actions.add_widget(Action(icon="bell-outline", bg=MINT, fg=PRIMARY,
                                         width=40, height=40, radius=20, callback=self.notifications))
        header_actions.add_widget(Action(icon="account-outline", bg=MINT, fg=PRIMARY,
                                         width=40, height=40, radius=20, callback=self.account))
        self.header.add_widget(header_actions)
        self.shell.add_widget(self.header)
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), bar_color=(0, .32, .27, .2))
        self.content = column(spacing=16, padding=[18, 18, 18, 26], adaptive=True)
        self.scroll.add_widget(self.content)
        self.shell.add_widget(self.scroll)
        self.nav = Card(bg=WHITE, radius=0, orientation="horizontal", adaptive=False,
                        size_hint_y=None, height=dp(68), padding=[dp(12), dp(6)], spacing=6)
        self.shell.add_widget(self.nav)
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
                self.nav.add_widget(Action(title, icon=icon, vertical=True, font_size=10,
                                           bg=PRIMARY, fg=WHITE, callback=self.qr_info))
            else:
                self.nav.add_widget(Action(title, icon=icon, vertical=True, font_size=10,
                                           bg=MINT if title == page else WHITE,
                                           fg=PRIMARY if title == page else MUTED,
                                           callback=partial(self.show, title)))
        {"Inicio": self.home, "Mascotas": self.pets, "Rutina": self.routine, "Salud": self.health}[page]()
        self.scroll.scroll_y = 1
        Animation.cancel_all(self.content, "opacity")
        self.content.opacity = 1
        for index, widget in enumerate(reversed(self.content.children)):
            if index >= 6:
                break
            widget.opacity = 0
            def reveal(_, item=widget):
                if item.parent is self.content:
                    Animation(opacity=1, duration=.25, t="out_quad").start(item)
            Clock.schedule_once(reveal, index * .045)


    def heading(self, title, subtitle, badge=None):
        box = column(adaptive=True, spacing=3)
        if badge:
            line = row(height=25)
            tag = pill(badge, icon="check-decagram")
            tag.size_hint_x = .78
            line.add_widget(tag)
            line.add_widget(Text("", size_hint_x=.22))
            box.add_widget(line)
        box.add_widget(Text(title, 23, INK, bold=True, height=31))
        box.add_widget(Text(subtitle, 12, MUTED, height=22))
        self.content.add_widget(box)


    def detail_row(self, icon, title, detail, warm=False):
        line = row(height=50, spacing=12)
        line.add_widget(icon_tile(icon, bg=PEACH if warm else MINT))
        copy = column(spacing=2)
        copy.add_widget(Text(title, 16, INK, bold=True, height=26, shorten=True))
        copy.add_widget(Text(detail, 11, MUTED, height=22, shorten=True))
        line.add_widget(copy)
        return line


    def link_card(self, icon, title, detail, page, warm=False):
        card = Card(padding=12, spacing=0)
        line = row(height=52, spacing=10)
        line.add_widget(self.detail_row(icon, title, detail, warm))
        line.add_widget(Action(icon="arrow-right", width=38, bg=MINT, fg=PRIMARY,
                               callback=partial(self.show, page), radius=19))
        card.add_widget(line)
        return card


    def select_pet(self, pet_id, *_):
        self.selected_pet = pet_id
        self.show("Salud")


    def dialog(self, title, height=360):
        modal = ModalView(size_hint=(.92, None), height=dp(height), background_color=(0, 0, 0, 0),
                          overlay_color=(.02, .12, .10, .45))
        card = Card(adaptive=False, padding=22, spacing=14)
        top = row(height=36)
        top.add_widget(Text(title, 20, INK, bold=True))
        top.add_widget(Action(icon="close", width=36, height=36, bg=MINT, fg=PRIMARY, callback=lambda *_: modal.dismiss()))
        card.add_widget(top)
        modal.add_widget(card)
        return modal, card


    def message(self, title, body):
        modal, card = self.dialog(title, 330)
        card.add_widget(Text(body, 14, MUTED))
        card.add_widget(Action("Entendido", callback=lambda *_: modal.dismiss()))
        modal.open()


