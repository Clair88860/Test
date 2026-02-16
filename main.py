import os
import struct
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.camera import Camera
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.utils import platform

# Android BLE Imports
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# ===== BLE Callbacks =====
class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app
    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, scanRecord):
        if device.getName() == "Arduino_GCS":
            self.app.connect(device)

class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app
    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:
            Clock.schedule_once(lambda dt: gatt.discoverServices(),1)
    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        services = gatt.getServices()
        for i in range(services.size()):
            s = services.get(i)
            if "180a" in s.getUuid().toString().lower():
                chars = s.getCharacteristics()
                for j in range(chars.size()):
                    c = chars.get(j)
                    if "2a57" in c.getUuid().toString().lower():
                        gatt.setCharacteristicNotification(c, True)
                        d = c.getDescriptor(UUID.fromString(CCCD_UUID))
                        if d:
                            d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                            gatt.writeDescriptor(d)
    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):
        data = characteristic.getValue()
        if data:
            try:
                angle = struct.unpack('<h', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_angle(angle))
            except:
                pass

# ===== Main App =====
class MainApp(App):
    def build(self):
        self.user_data_dir = App.get_running_app().user_data_dir

        self.root = BoxLayout(orientation="vertical")

        # ===== Dashboard Buttons oben =====
        self.dashboard = BoxLayout(size_hint_y=0.1)
        self.btn_camera = Button(text="K"); self.btn_camera.bind(on_press=self.show_camera)
        self.btn_gallery = Button(text="G"); self.btn_gallery.bind(on_press=self.show_gallery)
        self.btn_e = Button(text="E"); self.btn_e.bind(on_press=self.show_e)
        self.btn_a = Button(text="A"); self.btn_a.bind(on_press=self.show_a)
        for b in [self.btn_camera,self.btn_gallery,self.btn_e,self.btn_a]:
            self.dashboard.add_widget(b)
        self.root.add_widget(self.dashboard)

        # ===== Content Bereich =====
        self.content = BoxLayout()
        self.root.add_widget(self.content)

        # Arduino Werte
        self.arduino_enabled = False
        self.angle = 0
        self.direction = "--"

        # BLE
        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None

        # Startseite Kamera
        self.show_camera()

        # Dashboard Update jede Sekunde
        Clock.schedule_interval(lambda dt: self.update_dashboard(), 1)

        return self.root

    # ===== Update BLE Winkel =====
    def update_angle(self, angle):
        self.angle = angle
        self.direction = self.calc_direction(angle)
        if hasattr(self,'arduino_label'):
            self.arduino_label.text = f"Winkel: {self.angle}° | Richtung: {self.direction}"

    def calc_direction(self, angle):
        a = angle % 360
        if a>=337 or a<22: return "Nord"
        if a<67: return "Nordost"
        if a<112: return "Ost"
        if a<157: return "Südost"
        if a<202: return "Süd"
        if a<247: return "Südwest"
        if a<292: return "West"
        return "Nordwest"

    def update_dashboard(self):
        # Dashboard oben bleibt sichtbar, keine Änderung nötig
        pass

    # ===== Camera =====
    def show_camera(self,*args):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")

        self.camera = Camera(play=True)
        layout.add_widget(self.camera)

        btn = Button(text="Foto aufnehmen",size_hint_y=0.15)
        layout.add_widget(btn)
        self.content.add_widget(layout)

    # ===== Gallery =====
    def show_gallery(self,*args):
        self.content.clear_widgets()
        lbl = Label(text="Galerie (Demo)")
        self.content.add_widget(lbl)

    # ===== A-Seite: Arduino Daten =====
    def show_a(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical")
        self.arduino_label = Label(text=f"Winkel: {self.angle}° | Richtung: {self.direction}", size_hint_y=None,height=40)
        vbox.add_widget(self.arduino_label)
        self.content.add_widget(vbox)

    # ===== E-Seite: Einstellungen mit farbigen Ja/Nein =====
    def show_e(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical", padding=10, spacing=10)
        # Arduino aktiviert
        h1 = BoxLayout()
        h1.add_widget(Label(text="Mit Arduino"))
        ja = ToggleButton(text="Ja", group="arduino"); nein = ToggleButton(text="Nein", group="arduino", state="down")
        ja.bind(on_press=lambda x: setattr(self,'arduino_enabled', True))
        nein.bind(on_press=lambda x: setattr(self,'arduino_enabled', False))
        h1.add_widget(ja); h1.add_widget(nein)
        vbox.add_widget(h1)
        # Zentrierung
        h2 = BoxLayout()
        h2.add_widget(Label(text="Zentrierung"))
        ja2 = ToggleButton(text="Ja", group="zent"); nein2 = ToggleButton(text="Nein", group="zent", state="down")
        h2.add_widget(ja2); h2.add_widget(nein2)
        vbox.add_widget(h2)
        # Automatisches Speichern
        h3 = BoxLayout()
        h3.add_widget(Label(text="Automatisches Speichern"))
        ja3 = ToggleButton(text="Ja", group="auto"); nein3 = ToggleButton(text="Nein", group="auto", state="down")
        h3.add_widget(ja3); h3.add_widget(nein3)
        vbox.add_widget(h3)
        # Mit Winkel
        h4 = BoxLayout()
        h4.add_widget(Label(text="Mit Winkel"))
        ja4 = ToggleButton(text="Ja", group="winkel"); nein4 = ToggleButton(text="Nein", group="winkel", state="down")
        h4.add_widget(ja4); h4.add_widget(nein4)
        vbox.add_widget(h4)

        self.content.add_widget(vbox)
