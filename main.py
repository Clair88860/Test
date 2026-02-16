from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from jnius import autoclass
import os
import datetime

# Android Permissions
if platform == "android":
    from android.permissions import request_permissions, Permission

# ───────────── Design ─────────────
DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)
TEXT_COLOR = (1, 1, 1, 1)
BUTTON_COLOR = (0.2, 0.6, 0.2, 1)

# ───────────── Screens ─────────────
class HScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Label(
            text="Bei Problemen melden sie sich bitte unter folgender E-Mail Adresse:",
            color=TEXT_COLOR,
            halign="center",
            valign="middle",
            font_size=32
        ))

class KScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.layout = BoxLayout(orientation='vertical')
        self.add_widget(self.layout)

        # Kamera Bereich
        self.camera_area = BoxLayout()
        self.layout.add_widget(self.camera_area)

        # Button unten auf Kamera
        self.capture_btn = Button(
            text="●",
            size_hint=(None, None),
            size=(80, 80),
            background_normal='',
            background_color=(1,1,1,1),
            pos_hint={'center_x':0.5}
        )
        self.capture_btn.bind(on_press=self.capture)
        self.layout.add_widget(self.capture_btn)

        # Platz für Vorschau
        self.preview = None

    def capture(self, instance):
        # Kamera aufnehmen
        if self.app.autom_save:
            self.app.save_photo()
        else:
            # Vorschau anzeigen mit Wiederholen/Speichern
            if self.preview:
                self.layout.remove_widget(self.preview)
            self.preview = Image(source=self.app.take_photo(), allow_stretch=True)
            self.layout.add_widget(self.preview, index=1)  # Über Button
            # Buttons unter Vorschau
            btn_layout = BoxLayout(size_hint=(1,0.1))
            btn_repeat = Button(text="Wiederholen", on_press=lambda x:self.app.repeat_photo(self.preview))
            btn_save = Button(text="Speichern", on_press=lambda x:self.app.save_preview(self.preview))
            btn_layout.add_widget(btn_repeat)
            btn_layout.add_widget(btn_save)
            self.layout.add_widget(btn_layout)
            self.app.current_preview_btn_layout = btn_layout

class GScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        scroll = ScrollView()
        scroll.add_widget(self.grid)
        self.add_widget(scroll)
        self.refresh_gallery()

    def refresh_gallery(self):
        self.grid.clear_widgets()
        photos = sorted(self.app.photos)
        for idx, path in enumerate(photos):
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=200)
            thumb = Image(source=path)
            box.add_widget(Label(text=f"{idx+1:04d}", size_hint_y=0.1))
            box.add_widget(thumb)
            i_btn = Button(text="i", size_hint=(0.1,0.1))
            i_btn.bind(on_press=lambda x, p=path: self.app.open_photo_info(p))
            box.add_widget(i_btn)
            self.grid.add_widget(box)

class EScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=0.1))
        # Optionen
        self.options = {
            "Automatisches Speichern": "autom_save",
            "Daten von Arduino": "arduino_data",
            "Mit Entzerrung": "entzerrung",
            "Mit Winkel": "winkel"
        }
        for key, attr in self.options.items():
            row = BoxLayout(size_hint_y=0.1)
            row.add_widget(Label(text=key, size_hint_x=0.6))
            btn_yes = Button(text="Ja", background_color=BUTTON_COLOR)
            btn_no = Button(text="Nein")
            btn_yes.bind(on_press=lambda x, a=attr: self.app.set_option(a, True))
            btn_no.bind(on_press=lambda x, a=attr: self.app.set_option(a, False))
            row.add_widget(btn_yes)
            row.add_widget(btn_no)
            layout.add_widget(row)
        self.add_widget(layout)

class AScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(Label(text="BLE Arduino Daten Seite", font_size=24))
        self.add_widget(layout)

# ───────────── Main App ─────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("settings.json")
        self.photos = []
        self.autom_save = self.store.get('settings')['autom_save'] if self.store.exists('settings') else False
        self.arduino_data = self.store.get('settings')['arduino_data'] if self.store.exists('settings') else False
        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(HScreen(name='H'))
        self.sm.add_widget(KScreen(self, name='K'))
        self.sm.add_widget(GScreen(self, name='G'))
        self.sm.add_widget(EScreen(self, name='E'))
        self.sm.add_widget(AScreen(name='A'))
        # Immer K öffnen
        self.sm.current = 'K'
        return self.sm

    # Dummy Kamera Funktionen
    def take_photo(self):
        filename = f"photo_{len(self.photos)+1:04d}.png"
        self.photos.append(filename)
        # In echter App hier Kamera-Bild speichern
        return filename

    def save_photo(self):
        photo = self.take_photo()
        self.photos.append(photo)
        self.sm.get_screen('G').refresh_gallery()

    def repeat_photo(self, preview):
        # Entferne Vorschau
        screen = self.sm.get_screen('K')
        screen.layout.remove_widget(preview)
        screen.layout.remove_widget(screen.app.current_preview_btn_layout)
        screen.preview = None

    def save_preview(self, preview):
        # Speichern
        self.photos.append(preview.source)
        self.sm.get_screen('G').refresh_gallery()
        self.repeat_photo(preview)

    def open_photo_info(self, path):
        # Popup mit Name editierbar, Datum/Uhrzeit, Löschen
        box = BoxLayout(orientation='vertical')
        lbl_name = Label(text=os.path.basename(path))
        box.add_widget(lbl_name)
        lbl_date = Label(text=str(datetime.datetime.now()))
        box.add_widget(lbl_date)
        btn_del = Button(text="Foto löschen")
        box.add_widget(btn_del)
        popup = Popup(title="Info", content=box, size_hint=(0.8,0.5))
        popup.open()

    def set_option(self, attr, val):
        setattr(self, attr, val)
        if not self.store.exists('settings'):
            self.store.put('settings', **{attr: val})
        else:
            self.store.update('settings', **{attr: val})

if __name__ == "__main__":
    MainApp().run()
