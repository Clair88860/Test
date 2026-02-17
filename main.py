from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity


SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"
CCCD_UUID    = "00002902-0000-1000-8000-00805f9b34fb"


class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, scanRecord):
        name = device.getName()
        self.app.log(f"Gefunden: {name}")

        if name == "Arduino_GCS":
            self.app.log("Arduino erkannt – verbinde...")
            BluetoothAdapter.getDefaultAdapter().stopLeScan(self.app.scan_cb)
            self.app.connect(device)


class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:
            self.app.log("Verbunden")
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1)
        elif newState == 0:
            self.app.log("Getrennt")

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")

        service = gatt.getService(UUID.fromString(SERVICE_UUID))
        if not service:
            self.app.log("Service NICHT gefunden")
            return

        characteristic = service.getCharacteristic(UUID.fromString(CHAR_UUID))
        if not characteristic:
            self.app.log("Characteristic NICHT gefunden")
            return

        gatt.setCharacteristicNotification(characteristic, True)

        descriptor = characteristic.getDescriptor(UUID.fromString(CCCD_UUID))
        descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        gatt.writeDescriptor(descriptor)

        self.app.log("Notifications aktiviert")

    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):
        data = bytes(characteristic.getValue())
        direction = data.decode("utf-8")
        Clock.schedule_once(lambda dt: self.app.update_direction(direction))


class BLEApp(App):

    def build(self):

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.direction_label = Label(text="---", font_size=70, size_hint_y=0.3)

        self.scan_btn = Button(text="Scan starten", size_hint_y=0.15)
        self.scan_btn.bind(on_press=self.start_scan)

        self.log_label = Label(text="Bereit\n", size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter('size'))

        scroll = ScrollView(size_hint_y=0.4)
        scroll.add_widget(self.log_label)

        layout.add_widget(self.direction_label)
        layout.add_widget(self.scan_btn)
        layout.add_widget(scroll)

        self.scan_cb = None
        self.gatt = None

        return layout

    def log(self, text):
        Clock.schedule_once(lambda dt:
            setattr(self.log_label, "text", self.log_label.text + text + "\n"))

    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT
            ], lambda x, y: None)

    def start_scan(self, instance):

        adapter = BluetoothAdapter.getDefaultAdapter()

        if not adapter:
            self.log("Kein Bluetooth Adapter")
            return

        if not adapter.isEnabled():
            self.log("Bluetooth ist AUS")
            return

        self.log("Scan gestartet...")
        self.scan_cb = BLEScanCallback(self)
        adapter.startLeScan(self.scan_cb)

    def connect(self, device):
        self.log("Verbinde...")
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb)

    def update_direction(self, direction):
        self.direction_label.text = direction
        self.log(f"Neue Richtung: {direction}")


if __name__ == "__main__":
    BLEApp().run()
