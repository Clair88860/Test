import os
import time
import struct
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import platform
from kivy.uix.camera import Camera

# ================= BLE (Android only) =================

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"


# ================= HAUPT APP =================

class MainApp(App):

    def build(self):
        self.root = BoxLayout(orientation="vertical")

        # Dashboard oben
        self.topbar = Label(
            text="Winkel: --° | Richtung: --",
            size_hint_y=0.1,
            font_size=22
        )

        self.content = BoxLayout()
        self.root.add_widget(self.topbar)
        self.root.add_widget(self.content)

        self.angle = 0
        self.direction = "--"

        self.show_camera()

        return self.root

    # =========================================================
    # =================== BLE FUNKTIONEN ======================
    # =========================================================

    def start_scan(self):
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            self.scan_cb = self.BLEScanCallback(self)
            adapter.startLeScan(self.scan_cb)
        except:
            self.topbar.text = "Bluetooth Fehler"

    class BLEScanCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
        def onLeScan(self, device, rssi, scanRecord):
            if device.getName() == "Arduino_GCS":
                adapter = BluetoothAdapter.getDefaultAdapter()
                adapter.stopLeScan(self)
                self.app.connect(device)

    def connect(self, device):
        self.gatt_cb = self.GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb)

    class GattCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
        def onCharacteristicChanged(self, gatt, characteristic):
            data = characteristic.getValue()
            if data:
                angle = struct.unpack('<h', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_angle(angle))

    def update_angle(self, angle):
        self.angle = angle
        self.direction = self.get_direction(angle)
        self.topbar.text = f"Winkel: {angle}° | Richtung: {self.direction}"

    def get_direction(self, a):
        if a >= 337 or a < 22: return "Nord"
        if a < 67: return "Nordost"
        if a < 112: return "Ost"
        if a < 157: return "Suedost"
        if a < 202: return "Sued"
        if a < 247: return "Suedwest"
        if a < 292: return "West"
        return "Nordwest"

    # =========================================================
    # =================== KAMERA SEITE ========================
    # =========================================================

    def show_camera(self):
        self.content.clear_widgets()

        layout = BoxLayout(orientation="vertical")

        self.camera = Camera(play=True)
        layout.add_widget(self.camera)

        btn = Button(text="Foto aufnehmen", size_hint_y=0.15)
        btn.bind(on_press=self.capture)
        layout.add_widget(btn)

        self.content.add_widget(layout)

    def capture(self, instance):
        timestamp = int(time.time())
        filename = f"{timestamp}.png"
        path = os.path.join(self.user_data_dir, filename)
        self.camera.export_to_png(path)

        self.show_preview(path)

    def show_preview(self, path):
        self.content.clear_widgets()

        layout = BoxLayout(orientation="vertical")

        img = Image(source=path)
        layout.add_widget(img)

        buttons = BoxLayout(size_hint_y=0.2)

        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")

        save.bind(on_press=lambda x: self.show_camera())
        repeat.bind(on_press=lambda x: self.show_camera())

        buttons.add_widget(save)
        buttons.add_widget(repeat)

        layout.add_widget(buttons)
        self.content.add_widget(layout)

    # =========================================================
    # =================== GALERIE =============================
    # =========================================================

    def show_gallery(self):
        self.content.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted(os.listdir(self.user_data_dir))

        for f in files:
            if f.endswith(".png"):
                box = BoxLayout(orientation="vertical", size_hint_y=None, height=500)

                lbl = Label(text=f)
                img = Image(source=os.path.join(self.user_data_dir, f))

                box.add_widget(lbl)
                box.add_widget(img)
                grid.add_widget(box)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =========================================================
    # =================== E SEITE =============================
    # =========================================================

    def show_e(self):
        self.content.clear_widgets()

        layout = BoxLayout(orientation="vertical", spacing=20, padding=20)

        def row(title):
            r = BoxLayout()
            r.add_widget(Label(text=title))

            ja = ToggleButton(text="Ja", group=title)
            nein = ToggleButton(text="Nein", group=title)

            def toggle(btn):
                if btn.state == "down":
                    btn.background_color = (0,0.5,0,1)
                else:
                    btn.background_color = (1,1,1,1)

            ja.bind(on_press=toggle)
            nein.bind(on_press=toggle)

            r.add_widget(ja)
            r.add_widget(nein)
            return r

        layout.add_widget(row("Mit Arduino"))
        layout.add_widget(row("Mit Entzerrung"))
        layout.add_widget(row("Automatisches Speichern"))
        layout.add_widget(row("Mit Winkel"))

        scan_btn = Button(text="Scan starten", size_hint_y=0.2)
        scan_btn.bind(on_press=lambda x: self.start_scan())
        layout.add_widget(scan_btn)

        self.content.add_widget(layout)


if __name__ == "__main__":
    MainApp().run()
