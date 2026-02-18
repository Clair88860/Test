from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission

    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# -----------------------------
def direction_from_angle(angle):
    if angle >= 337 or angle < 22: return "Nord"
    if angle < 67: return "Nordost"
    if angle < 112: return "Ost"
    if angle < 157: return "Südost"
    if angle < 202: return "Süd"
    if angle < 247: return "Südwest"
    if angle < 292: return "West"
    return "Nordwest"

# -----------------------------
# BLE Scan Callback für startLeScan()
# -----------------------------
if platform == "android":
    class BLEScanCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
        def onLeScan(self, device, rssi, scanRecord):
            name = device.getName()
            if name == "Arduino_GCS":
                self.app.log(f"Gerät gefunden: {name}")
                self.app.stop_scan()
                Clock.schedule_once(lambda dt: self.app.connect(device), 0.5)

# -----------------------------
class BLEApp(App):

    def build(self):
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.angle_label = Label(text="0° – Nord", font_size=60)
        self.button = Button(text="Scan starten", on_press=self.start_scan)
        self.log_label = Label(text="Bereit\n", size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView()
        scroll.add_widget(self.log_label)
        layout.add_widget(self.angle_label)
        layout.add_widget(self.button)
        layout.add_widget(scroll)

        if platform == "android":
            request_permissions([
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT,
                Permission.ACCESS_FINE_LOCATION
            ])
            self.adapter = BluetoothAdapter.getDefaultAdapter()
            self.scan_cb = None
            self.gatt = None

        return layout

    # -----------------------------
    def log(self, txt):
        Clock.schedule_once(lambda dt:
            setattr(self.log_label, "text", self.log_label.text + txt + "\n")
        )

    # -----------------------------
    def start_scan(self, *args):
        if platform != "android":
            return
        try:
            if not self.adapter or not self.adapter.isEnabled():
                self.log("Bluetooth nicht aktiviert")
                return
            self.log("Scan starten...")
            self.scan_cb = BLEScanCallback(self)
            self.adapter.startLeScan(self.scan_cb)
        except Exception as e:
            self.log(f"Scan Fehler: {e}")

    # -----------------------------
    def stop_scan(self):
        if self.adapter and self.scan_cb:
            try:
                self.adapter.stopLeScan(self.scan_cb)
                self.log("Scan gestoppt")
            except:
                pass

    # -----------------------------
    def connect(self, device):
        try:
            self.log(f"Verbinde mit {device.getAddress()}...")
            self.gatt = device.connectGatt(mActivity, False, None, 2)
            self.log("✅ Connected (GATT ohne Callback, Notifications können direkt gelesen werden)")
        except Exception as e:
            self.log(f"Connect Fehler: {e}")

    # -----------------------------
    def update_angle(self, angle):
        direction = direction_from_angle(angle)
        self.angle_label.text = f"{angle}° – {direction}"

    def on_stop(self):
        if platform == "android" and self.gatt:
            self.gatt.close()

if __name__ == "__main__":
    BLEApp().run()
