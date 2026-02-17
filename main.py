from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct

# Android-spezifische Importe
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

# ----- Richtung aus Winkel -----
def direction_from_angle(angle):
    if angle >= 337 or angle < 22: return "Nord"
    if angle < 67: return "Nordost"
    if angle < 112: return "Ost"
    if angle < 157: return "Südost"
    if angle < 202: return "Süd"
    if angle < 247: return "Südwest"
    if angle < 292: return "West"
    return "Nordwest"

# ----- BLE Scan Callback -----
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

# ----- GATT Callback -----
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
            self.app.log(f"Service UUID: {s_uuid}")
            chars = s.getCharacteristics()
            for j in range(chars.size()):
                c = chars.get(j)
                c_uuid = c.getUuid().toString().lower()
                self.app.log(f"Characteristic UUID: {c_uuid}")
                # Arduino Winkel-Characteristic
                if "2a57" in c_uuid:
                    self.app.log(f"Winkel-Characteristic gefunden: {c_uuid}")
                    gatt.setCharacteristicNotification(c, True)
                    d = c.getDescriptor(UUID.fromString(CCCD_UUID))
                    if d:
                        d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                        gatt.writeDescriptor(d)
                        self.app.log("Notifications aktiviert")

    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):
        data = characteristic.getValue()
        self.app.log(f"Daten empfangen: {list(data)}")
        if data:
            try:
                # 32-bit signed int vom Arduino
                angle = struct.unpack('<i', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_data(angle))
            except Exception as e:
                self.app.log(f"Fehler bei Datenkonvertierung: {str(e)}")

# ----- Kivy App -----
class BLEApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.angle_lbl = Label(text="0° – Nord", font_size=60, size_hint_y=0.3)
        self.status_btn = Button(text="Scan starten", size_hint_y=0.15, on_press=self.start_scan)
        self.scroll = ScrollView(size_hint_y=0.55)
        self.log_lbl = Label(text="Bereit\n", size_hint_y=None, halign="left", valign="top")
        self.log_lbl.bind(texture_size=self.log_lbl.setter('size'))
        self.scroll.add_widget(self.log_lbl)

        self.root.add_widget(self.angle_lbl)
        self.root.add_widget(self.status_btn)
        self.root.add_widget(self.scroll)

        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None
        return self.root

    # ----- Logging -----
    def log(self, txt):
        Clock.schedule_once(lambda dt: setattr(self.log_lbl, 'text', self.log_lbl.text + txt + "\n"))

    # ----- Android Berechtigungen -----
    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT
            ], self.check_permissions)

    def check_permissions(self, permissions, results):
        if all(results):
            self.log("Alle Berechtigungen erteilt.")
        else:
            self.log("Berechtigungen fehlen!")

    # ----- BLE Scan starten -----
    def start_scan(self, *args):
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.log("Bitte Bluetooth aktivieren!")
                return
            self.log("Scanne...")
            self.status_btn.text = "Suche..."
            self.scan_cb = BLEScanCallback(self)
            adapter.startLeScan(self.scan_cb)
        except Exception as e:
            self.log(f"Scan Fehler: {str(e)}")

    # ----- Verbindung aufbauen -----
    def connect(self, device):
        adapter = BluetoothAdapter.getDefaultAdapter()
        adapter.stopLeScan(self.scan_cb)
        self.log(f"Verbinde mit {device.getAddress()}...")
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb, 2)  # TRANSPORT_LE

    # ----- Winkel und Richtung anzeigen -----
    def update_data(self, angle):
        dir_text = direction_from_angle(angle)
        self.angle_lbl.text = f"{angle}° – {dir_text}"
        self.status_btn.text = "Daten empfangen"

    # ----- BLE sauber schließen -----
    def on_stop(self):
        if self.gatt:
            self.gatt.close()

# ----- App starten -----
if __name__ == "__main__":
    BLEApp().run()
