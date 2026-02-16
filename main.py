import os
import datetime

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.metrics import dp

# ANDROID BLE
from jnius import autoclass, PythonJavaClass, java_method
from android import activity

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothGattCallback = autoclass('android.bluetooth.BluetoothGattCallback')
UUID = autoclass('java.util.UUID')

SERVICE_UUID = UUID.fromString("0000ffe0-0000-1000-8000-00805f9b34fb")
CHAR_UUID = UUID.fromString("0000ffe1-0000-1000-8000-00805f9b34fb")


# =========================================================
# BLE CALLBACK KLASSE (WICHTIG)
# =========================================================

class GattCallback(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/BluetoothGattCallback']
    __javacontext__ = 'app'

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method('(Landroid/bluetooth/BluetoothGatt;II)V')
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:  # connected
            self.app.arduino_connected = True
            gatt.discoverServices()

    @java_method('(Landroid/bluetooth/BluetoothGatt;I)V')
    def onServicesDiscovered(self, gatt, status):
        service = gatt.getService(SERVICE_UUID)
        if service:
            char = service.getCharacteristic(CHAR_UUID)
            gatt.setCharacteristicNotification(char, True)

    @java_method('(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V')
    def onCharacteristicChanged(self, gatt, characteristic):
        try:
            value = characteristic.getValue().decode("utf-8")
            self.app.update_north(value)
        except:
            pass


# =========================================================
# HAUPT APP
# =========================================================

class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        self.bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        self.gatt = None
        self.arduino_connected = False
        self.north_value = "--"

        self.build_topbar()
        self.build_camera()

    # =====================================================
    # UI
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1,.08),
                                pos_hint={"top":1})

        for text,func in [("K",self.show_camera),
                          ("G",self.show_gallery),
                          ("E",self.show_settings),
                          ("A",self.show_a),
                          ("H",self.show_help)]:
            b = Button(text=text)
            b.bind(on_press=func)
            self.topbar.add_widget(b)

        self.add_widget(self.topbar)

        self.north_label = Label(
            text="N: --°",
            size_hint=(None,None),
            size=(dp(120),dp(40)),
            pos_hint={"right":1,"top":.92}
        )
        self.add_widget(self.north_label)

    def build_camera(self):
        self.camera = Camera(play=True,
                             resolution=(640,480),
                             size_hint=(1,.9),
                             pos_hint={"top":.92})
        self.add_widget(self.camera)

    # =====================================================
    # BLE
    # =====================================================

    def scan_ble(self):

        if not self.bluetoothAdapter:
            return

        devices = self.bluetoothAdapter.getBondedDevices().toArray()

        for device in devices:
            name = device.getName()
            if name and "Arduino" in name:
                callback = GattCallback(self)
                self.gatt = device.connectGatt(None, False, callback)
                return

    def update_north(self, value):
        try:
            self.north_value = value
            self.north_label.text = f"N: {value}°"
        except:
            pass

    # =====================================================
    # SEITEN
    # =====================================================

    def show_camera(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.build_camera()

    def show_a(self,*args):
        self.clear_widgets()
        self.build_topbar()

        arduino_on = False
        if self.store.exists("arduino"):
            arduino_on = self.store.get("arduino")["value"]

        if not arduino_on:
            self.add_widget(Label(
                text="Sie müssen die Daten erst in den Einstellungen aktivieren",
                pos_hint={"center_x":.5,"center_y":.5}
            ))
            return

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=20,
                           pos_hint={"center_y":.5})

        status = Label(text="Scan nach Arduino...")
        layout.add_widget(status)

        scan_btn = Button(text="Verbinden")
        scan_btn.bind(on_press=lambda x:self.scan_ble())
        layout.add_widget(scan_btn)

        self.add_widget(layout)

    def show_settings(self,*args):
        self.clear_widgets()
        self.build_topbar()

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=20)

        label = Label(text="Daten von Arduino?")
        layout.add_widget(label)

        yes = Button(text="JA")
        no = Button(text="NEIN")

        yes.bind(on_press=lambda x:self.store.put("arduino",value=True))
        no.bind(on_press=lambda x:self.store.put("arduino",value=False))

        layout.add_widget(yes)
        layout.add_widget(no)

        self.add_widget(layout)

    def show_gallery(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.add_widget(Label(text="Galerie folgt..."))

    def show_help(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.add_widget(Label(
            text="Bei Fragen oder Problemen\nmelden Sie sich per E-Mail."
        ))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
