import os
import struct
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.togglebutton import ToggleButton
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
    # Dummy für PC Test
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# ====== BLE Callback Klassen ======
class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, scanRecord):
        name = device.getName()
        if name == "Arduino_GCS":
            self.app.log(f"Gefunden: {name}")
            self.app.connect(device)

class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:  # STATE_CONNECTED
            self.app.log("Verbunden! Suche Services...")
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1.0)
        elif newState == 0:  # STATE_DISCONNECTED
            self.app.log("Verbindung getrennt.")

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")
        services = gatt.getServices()
        for i in range(services.size()):
            s = services.get(i)
            s_uuid = s.getUuid().toString().lower()
            if "180a" in s_uuid:
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
            except Exception as e:
                self.app.log(f"Fehler: {str(e)}")

# ====== Main App ======
class MainApp(App):

    def build(self):
        self.root = BoxLayout(orientation="vertical")

        # Dashboard oben
        self.topbar = Label(text="Winkel: --° | Richtung: --", size_hint_y=0.1, font_size=22)
        self.root.add_widget(self.topbar)

        # Content Bereich
        self.content = BoxLayout()
        self.root.add_widget(self.content)

        # App Status
        self.arduino_enabled = False
        self.angle = 0
        self.direction = "--"

        # BLE
        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None

        # Kamera Start
        self.show_camera()

        # Dashboard Update jede Sekunde
        Clock.schedule_interval(lambda dt: self.update_dashboard(), 1.0)

        return self.root

    # ====== Dashboard Update ======
    def update_dashboard(self):
        self.topbar.text = f"Winkel: {self.angle}° | Richtung: {self.direction}"

    # Richtung aus Winkel berechnen
    def calc_direction(self, angle):
        a = angle % 360
        if a >= 337 or a < 22: return "Nord"
        if a < 67: return "Nordost"
        if a < 112: return "Ost"
        if a < 157: return "Südost"
        if a < 202: return "Süd"
        if a < 247: return "Südwest"
        if a < 292: return "West"
        return "Nordwest"

    def update_angle(self, angle):
        self.angle = angle
        self.direction = self.calc_direction(angle)

    # ====== Kamera ============================
    def show_camera(self):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")

        self.camera = Camera(play=True, resolution=(640,480))
        layout.add_widget(self.camera)

        # -90° Rotation
        with self.camera.canvas.before:
            from kivy.graphics import PushMatrix, PopMatrix, Rotate
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)

        btn = Button(text="Foto aufnehmen", size_hint_y=0.15)
        btn.bind(on_press=self.capture)
        layout.add_widget(btn)

        self.content.add_widget(layout)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def capture(self, instance):
        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])
        number = len(files) + 1
        filename = f"{number:04d}.png"
        path = os.path.join(self.user_data_dir, filename)
        self.camera.export_to_png(path)
        self.show_preview(path)

    def show_preview(self, path):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        img = Image(source=path)
        layout.add_widget(img)
        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")
        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save)
        btns.add_widget(repeat)
        layout.add_widget(btns)
        self.content.add_widget(layout)

    # ====== BLE Scan starten ======
    def start_scan(self, *args):
        if platform != "android": return
        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter or not adapter.isEnabled():
            self.log("Bitte Bluetooth aktivieren!")
            return
        self.log("Scanne nach Arduino...")
        self.scan_cb = BLEScanCallback(self)
        adapter.startLeScan(self.scan_cb)

    def connect(self, device):
        adapter = BluetoothAdapter.getDefaultAdapter()
        adapter.stopLeScan(self.scan_cb)
        self.log(f"Verbinde mit {device.getName()}...")
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb, 2)

    def log(self, text):
        print(text)  # kann man auf ein Label erweitern

if __name__ == "__main__":
    MainApp().run()
