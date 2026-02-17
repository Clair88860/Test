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
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# -----------------------------
# Richtungsberechnung
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
# Scan Callback
# -----------------------------
class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, scanRecord):
        name = device.getName()
        if name == "Arduino_GCS":
            self.app.log("Gerät gefunden – stoppe Scan")
            self.app.stop_scan()
            self.app.connect(device)

# -----------------------------
# GATT Callback
# -----------------------------
class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        self.app.log(f"Status: {status}, State: {newState}")

        if newState == 2:  # STATE_CONNECTED
            self.app.log("✅ Verbunden! Suche Services...")
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1.0)

        elif newState == 0:  # STATE_DISCONNECTED
            self.app.log("❌ Verbindung getrennt")

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")

        services = gatt.getServices()
        for i in range(services.size()):
            service = services.get(i)
            self.app.log(f"Service: {service.getUuid()}")

            chars = service.getCharacteristics()
            for j in range(chars.size()):
                char = chars.get(j)
                uuid = char.getUuid().toString().lower()
                self.app.log(f"Char: {uuid}")

                if "2a57" in uuid:
                    self.app.log("🎯 Winkel-Characteristic gefunden")

                    gatt.setCharacteristicNotification(char, True)
                    descriptor = char.getDescriptor(UUID.fromString(CCCD_UUID))

                    if descriptor:
                        descriptor.setValue(
                            BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                        )
                        gatt.writeDescriptor(descriptor)
                        self.app.log("Notifications aktiviert")

    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):
        data = characteristic.getValue()

        if data:
            try:
                angle = struct.unpack('<i', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_angle(angle))
            except Exception as e:
                self.app.log(f"Fehler beim Lesen: {e}")

# -----------------------------
# Haupt-App
# -----------------------------
class BLEApp(App):

    def build(self):
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.angle_label = Label(text="0° – Nord", font_size=60)
        self.button = Button(text="Scan starten", on_press=self.start_scan)

        self.log_label = Label(text="Bereit\n", size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter('size'))

        scroll = ScrollView()
        scroll.add_widget(self.log_label)

        self.layout.add_widget(self.angle_label)
        self.layout.add_widget(self.button)
        self.layout.add_widget(scroll)

        self.adapter = None
        self.scan_callback = None
        self.gatt = None
        self.gatt_callback = None

        return self.layout

    def log(self, text):
        Clock.schedule_once(lambda dt:
            setattr(self.log_label, "text", self.log_label.text + text + "\n")
        )

    # -----------------------------
    # Scan starten
    # -----------------------------
    def start_scan(self, *args):
        self.adapter = BluetoothAdapter.getDefaultAdapter()

        if not self.adapter or not self.adapter.isEnabled():
            self.log("Bluetooth ist nicht aktiviert")
            return

        self.log("Starte Scan...")
        self.scan_callback = BLEScanCallback(self)
        self.adapter.startLeScan(self.scan_callback)

    def stop_scan(self):
        if self.adapter and self.scan_callback:
            self.adapter.stopLeScan(self.scan_callback)
            self.log("Scan gestoppt")

    # -----------------------------
    # Verbinden
    # -----------------------------
    def connect(self, device):
        self.log("Versuche Verbindung...")

        self.gatt_callback = GattCallback(self)

        # 🔥 WICHTIG: autoConnect = False
        self.gatt = device.connectGatt(
            mActivity,
            False,
            self.gatt_callback,
            2  # TRANSPORT_LE
        )

    # -----------------------------
    # Anzeige aktualisieren
    # -----------------------------
    def update_angle(self, angle):
        direction = direction_from_angle(angle)
        self.angle_label.text = f"{angle}° – {direction}"

    def on_stop(self):
        if self.gatt:
            self.gatt.close()

# -----------------------------
if __name__ == "__main__":
    BLEApp().run()
