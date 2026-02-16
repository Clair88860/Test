import os
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.uix.popup import Popup
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import PushMatrix, PopMatrix, Rotate

from jnius import autoclass, PythonJavaClass, java_method

# ANDROID BLE
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothManager = autoclass('android.bluetooth.BluetoothManager')
BluetoothGattCallback = autoclass('android.bluetooth.BluetoothGattCallback')
ScanCallback = autoclass('android.bluetooth.le.ScanCallback')
UUID = autoclass('java.util.UUID')

SERVICE_UUID = UUID.fromString("0000180a-0000-1000-8000-00805f9b34fb")
CHAR_UUID = UUID.fromString("00002a57-0000-1000-8000-00805f9b34fb")


# =========================================================
# GATT CALLBACK (ECHT)
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
            self.app.status_text = "Verbunden ✔"
            gatt.discoverServices()

    @java_method('(Landroid/bluetooth/BluetoothGatt;I)V')
    def onServicesDiscovered(self, gatt, status):
        service = gatt.getService(SERVICE_UUID)
        if service:
            char = service.getCharacteristic(CHAR_UUID)
            gatt.setCharacteristicNotification(char, True)

    @java_method('(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V')
    def onCharacteristicChanged(self, gatt, characteristic):
        value = characteristic.getIntValue(0, 0)
        Clock.schedule_once(lambda dt: self.app.update_north(value))


# =========================================================
# SCAN CALLBACK
# =========================================================

class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/le/ScanCallback']
    __javacontext__ = 'app'

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method('(ILandroid/bluetooth/le/ScanResult;)V')
    def onScanResult(self, callbackType, result):
        device = result.getDevice()
        name = device.getName()
        if name and name == "Arduino_GCS":
            self.app.stop_scan()
            self.app.connect_device(device)


# =========================================================
# MAIN UI
# =========================================================

class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        self.adapter = BluetoothAdapter.getDefaultAdapter()
        self.scanner = None
        self.scan_callback = None
        self.gatt = None
        self.north_value = "--"

        self.build_topbar()
        self.build_camera()
        self.build_buttons()

    # =====================================================
    # UI
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1,.08),
                                pos_hint={"top":1})

        for t,f in [("K",self.show_camera),
                    ("G",self.show_gallery),
                    ("E",self.show_settings),
                    ("A",self.show_a),
                    ("H",self.show_help)]:
            b = Button(text=t)
            b.bind(on_press=f)
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

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.add_widget(self.camera)

    def build_buttons(self):
        self.capture_btn = Button(text="Speichern",
                                  size_hint=(None,None),
                                  size=(dp(120),dp(50)),
                                  pos_hint={"center_x":.5,"y":.02})
        self.capture_btn.bind(on_press=self.capture)
        self.add_widget(self.capture_btn)

        self.repeat_btn = Button(text="Wiederholen",
                                 size_hint=(None,None),
                                 size=(dp(120),dp(50)),
                                 pos_hint={"right":.95,"y":.02})
        self.repeat_btn.bind(on_press=lambda x:self.show_camera())
        self.add_widget(self.repeat_btn)

    # =====================================================
    # BLE
    # =====================================================

    def start_scan(self):
        if not self.adapter:
            return

        self.scanner = self.adapter.getBluetoothLeScanner()
        self.scan_callback = BLEScanCallback(self)
        self.scanner.startScan(self.scan_callback)

    def stop_scan(self):
        if self.scanner and self.scan_callback:
            self.scanner.stopScan(self.scan_callback)

    def connect_device(self, device):
        self.status_label.text = "Verbinde..."
        callback = GattCallback(self)
        self.gatt = device.connectGatt(None, False, callback)

    def update_north(self, value):
        self.north_value = value
        self.north_label.text = f"N: {value}°"
        if hasattr(self, "a_label"):
            self.a_label.text = f"Winkel: {value}°"

    # =====================================================
    # SEITEN
    # =====================================================

    def show_camera(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.build_camera()
        self.build_buttons()

    def show_a(self,*args):
        self.clear_widgets()
        self.build_topbar()

        if not self.store.exists("arduino") or not self.store.get("arduino")["value"]:
            self.add_widget(Label(
                text="Sie müssen die Daten erst in den Einstellungen aktivieren",
                pos_hint={"center_x":.5,"center_y":.5}
            ))
            return

        layout = BoxLayout(orientation="vertical",
                           spacing=20,
                           padding=20)

        self.status_label = Label(text="Bereit")
        layout.add_widget(self.status_label)

        self.a_label = Label(text="Winkel: --°",
                             font_size=24)
        layout.add_widget(self.a_label)

        scan_btn = Button(text="Scan starten")
        scan_btn.bind(on_press=lambda x:self.start_scan())
        layout.add_widget(scan_btn)

        self.add_widget(layout)

    def show_settings(self,*args):
        self.clear_widgets()
        self.build_topbar()

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=20)

        label = Label(text="Daten vom Arduino anzeigen?")
        layout.add_widget(label)

        yes = Button(text="JA", background_color=(0,1,0,1))
        no = Button(text="NEIN", background_color=(1,0,0,1))

        yes.bind(on_press=lambda x:self.store.put("arduino",value=True))
        no.bind(on_press=lambda x:self.store.put("arduino",value=False))

        layout.add_widget(yes)
        layout.add_widget(no)

        self.add_widget(layout)

    def show_gallery(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.add_widget(Label(text="Galerie folgt"))

    def show_help(self,*args):
        self.clear_widgets()
        self.build_topbar()
        self.add_widget(Label(
            text="Bei Fragen oder Problemen können Sie sich per E-Mail melden."
        ))

    # =====================================================
    # CAMERA SAVE
    # =====================================================

    def capture(self,*args):
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(App.get_running_app().user_data_dir,
                            f"IMG_{now}.png")
        self.camera.export_to_png(path)
        popup = Popup(title="Gespeichert",
                      content=Label(text="Bild gespeichert"),
                      size_hint=(.6,.3))
        popup.open()


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
