import os
import datetime
import struct
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform

try:
    from android.permissions import check_permission, request_permissions, Permission
except:
    check_permission = None
    request_permissions = None
    Permission = None

# Optional BLE imports
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
    UUID = autoclass("java.util.UUID")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore("settings.json")
        self.photos_dir = os.path.join(App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # BLE vars
        self.ble_active = False
        self.gatt = None
        self.scan_cb = None
        self.scanner = None
        self.gatt_cb = None

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()
        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # ================================
    # Topbar
    # ================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1}, spacing=5, padding=5)
        for t, f in [("K", self.show_camera), ("G", self.show_gallery), ("E", self.show_settings), ("A", self.show_arduino), ("H", self.show_help)]:
            b = Button(text=t, background_normal="", background_color=(0.15, 0.15, 0.15,1), color=(1,1,1,1))
            b.bind(on_press=f)
            self.topbar.add_widget(b)

    # ================================
    # Kamera
    # ================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920,1080))
        self.camera.size_hint = (1, .9)
        self.camera.pos_hint = {"center_x":.5, "center_y":.45}
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # ================================
    # Kamera Button
    # ================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None), size=(dp(80),dp(80)), pos_hint={"center_x":.5,"y":.04}, background_normal="", background_color=(0,0,0,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.outer_circle = Ellipse(size=self.capture.size, pos=self.capture.pos)
            Color(0.9,0.9,0.9,1)
            self.inner_circle = Ellipse(size=(dp(60),dp(60)), pos=(self.capture.x+dp(10), self.capture.y+dp(10)))
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size
        self.inner_circle.pos = (self.capture.x+dp(10), self.capture.y+dp(10))

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(text="Kamera Berechtigung fehlt", pos_hint={"center_x":.5,"center_y":.5}))
            return
        self.camera.play=True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # ================================
    # Fotos
    # ================================
    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    def take_photo(self, instance):
        auto_save = self.store.get("auto")["value"] if self.store.exists("auto") else False
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number+".png")
        self.camera.export_to_png(path)
        if auto_save:
            self.log(f"Foto {number} gespeichert")
        else:
            self.show_save_popup(path, number)

    def show_save_popup(self, path, number):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        lbl = Label(text=f"Foto {number} aufgenommen")
        btn_save = Button(text="Speichern")
        btn_repeat = Button(text="Wiederholen")
        layout.add_widget(lbl)
        layout.add_widget(btn_save)
        layout.add_widget(btn_repeat)
        popup = Popup(title="Foto aufnehmen", content=layout, size_hint=(.8,.5))
        btn_save.bind(on_press=lambda x: [popup.dismiss(), self.show_camera()])
        btn_repeat.bind(on_press=lambda x: [os.remove(path), popup.dismiss(), self.show_camera()])
        popup.open()

    # ================================
    # E Settings
    # ================================
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical", padding=[20,120,20,20], spacing=20)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None, height=dp(60)))
        for text,key in [("Mit Arduino Daten","arduino"),("Mit Winkel","winkel"),("Automatisch speichern","auto")]:
            row = BoxLayout(size_hint_y=None, height=dp(60))
            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(80),dp(45)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(80),dp(45)))
            value = self.store.get(key)["value"] if self.store.exists(key) else False
            def update(selected, ja=btn_ja, nein=btn_nein):
                if selected:
                    ja.background_color=(0,0.6,0,1)
                    nein.background_color=(1,1,1,1)
                else:
                    nein.background_color=(0,0.6,0,1)
                    ja.background_color=(1,1,1,1)
            update(value)
            btn_ja.bind(on_press=lambda x,key=key: [self.store.put(key,value=True), update(True)])
            btn_nein.bind(on_press=lambda x,key=key: [self.store.put(key,value=False), update(False)])
            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            layout.add_widget(row)
        self.add_widget(layout)

    # ================================
    # H Hilfe
    # ================================
    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Bei Fragen oder Problemen können Sie sich jederzeit gerne unter folgender E-Mail adresse melden:", pos_hint={"center_x":.5,"center_y":.5}))

    # ================================
    # A Arduino BLE
    # ================================
    def show_arduino(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if not self.store.exists("arduino") or not self.store.get("arduino")["value"]:
            self.add_widget(Label(text="Daten in den Einstellungen aktivieren", pos_hint={"center_x":.5,"center_y":.5}))
            return
        # BLE Live Anzeige Placeholder
        self.angle_label = Label(text="0°", font_size=50)
        self.add_widget(self.angle_label)
        self.status_label = Label(text="Scan starten")
        self.add_widget(self.status_label)
        # Hier BLE Scan starten, wenn Android BLE aktiv
        if platform == "android":
            self.start_ble_scan()

    # ================================
    # Logging
    # ================================
    def log(self, txt):
        print(txt)
