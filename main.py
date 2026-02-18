from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct

# -------------------------------------------------
# ANDROID IMPORTS
# -------------------------------------------------
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission

    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# -------------------------------------------------
def direction_from_angle(angle):
    if angle >= 337 or angle < 22: return "Nord"
    if angle < 67: return "Nordost"
    if angle < 112: return "Ost"
    if angle < 157: return "Südost"
    if angle < 202: return "Süd"
    if angle < 247: return "Südwest"
    if angle < 292: return "West"
    return "Nordwest"

# -------------------------------------------------
# SCAN CALLBACK (WICHTIG: __javaclass__)
# -------------------------------------------------
if platform == "android":
    class MyScanCallback(PythonJavaClass):
        __javaclass__ = "android/bluetooth/le/ScanCallback"

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(ILandroid/bluetooth/le/ScanResult;)V")
        def onScanResult(self, callbackType, result):
            device = result.getDevice()
            name = device.getName()

            if name == "Arduino_GCS":
                self.app.log("Gerät gefunden!")
                self.app.stop_scan()
                Clock.schedule_once(lambda dt: self.app.connect(device), 0.5)

# -------------------------------------------------
# GATT CALLBACK
# -------------------------------------------------
if platform == "android":
    class GattCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
        def onConnectionStateChange(self, gatt, status, newState):
            self.app.log(f"Status: {status}, State: {newState}")

            if newState == 2:
                self.app.log("✅ Verbunden – suche Services")
                Clock.schedule_once(lambda dt: gatt.discoverServices(), 1.0)
            elif newState == 0:
                self.app.log("❌ Getrennt")

        @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
        def onServicesDiscovered(self, gatt, status):
            self.app.log("Services entdeckt")

            services = gatt.getServices()
            for i in range(services.size()):
                service = services.get(i)
                chars = service.getCharacteristics()

                for j in range(chars.size()):
                    char = chars.get(j)
                    uuid = char.getUuid().toString().lower()

                    if "2a57" in uuid:
                        self.app.log("Winkel-Characteristic gefunden")

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
                angle = struct.unpack('<i', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_angle(angle))

# -------------------------------------------------
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
            self.scanner = None
            self.scan_callback = None
            self.gatt = None
            self.gatt_callback = None

        return layout

    # -------------------------------------------------
    def log(self, text):
        Clock.schedule_once(lambda dt:
            setattr(self.log_label, "text", self.log_label.text + text + "\n")
        )

    # -------------------------------------------------
    def start_scan(self, *args):
        if platform != "android":
            return

        try:
            if not self.adapter or not self.adapter.isEnabled():
                self.log("Bluetooth nicht aktiviert")
                return

            self.log("Starte Scan...")

            self.scanner = self.adapter.getBluetoothLeScanner()
            self.scan_callback = MyScanCallback(self)
            self.scanner.startScan(self.scan_callback)

        except Exception as e:
            self.log(f"Scan Fehler: {e}")

    # -------------------------------------------------
    def stop_scan(self):
        if self.scanner and self.scan_callback:
            try:
                self.scanner.stopScan(self.scan_callback)
                self.log("Scan gestoppt")
            except:
                pass

    # -------------------------------------------------
    def connect(self, device):
        try:
            self.log("Verbinde...")
            self.gatt_callback = GattCallback(self)
            self.gatt = device.connectGatt(
                mActivity,
                False,
                self.gatt_callback
            )
        except Exception as e:
            self.log(f"Connect Fehler: {e}")

    # -------------------------------------------------
    def update_angle(self, angle):
        direction = direction_from_angle(angle)
        self.angle_label.text = f"{angle}° – {direction}"

    def on_stop(self):
        if platform == "android" and self.gatt:
            self.gatt.close()

# -------------------------------------------------
if __name__ == "__main__":
    BLEApp().run()
