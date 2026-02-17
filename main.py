from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
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
        if device.getName() == "Arduino_GCS":
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
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1)

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):

        service = gatt.getService(UUID.fromString(SERVICE_UUID))
        characteristic = service.getCharacteristic(UUID.fromString(CHAR_UUID))

        gatt.setCharacteristicNotification(characteristic, True)

        descriptor = characteristic.getDescriptor(UUID.fromString(CCCD_UUID))
        descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        gatt.writeDescriptor(descriptor)

    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):

        data = bytes(characteristic.getValue())
        direction = data.decode("utf-8")

        Clock.schedule_once(lambda dt: self.app.update_direction(direction))


class BLEApp(App):

    def build(self):

        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)

        self.direction_label = Label(text="---", font_size=80)
        self.button = Button(text="Scan starten", size_hint_y=0.2)
        self.button.bind(on_press=self.start_scan)

        layout.add_widget(self.direction_label)
        layout.add_widget(self.button)

        self.scan_cb = None
        self.gatt_cb = None
        self.gatt = None

        return layout

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
        self.scan_cb = BLEScanCallback(self)
        adapter.startLeScan(self.scan_cb)

    def connect(self, device):
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb, 2)

    def update_direction(self, direction):
        self.direction_label.text = direction


if __name__ == "__main__":
    BLEApp().run()
