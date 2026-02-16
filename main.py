import os, struct
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.camera import Camera
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.utils import platform

IS_ANDROID = platform == "android"
if IS_ANDROID:
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

if IS_ANDROID:
    class BLEScanCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
        def __init__(self, app): super().__init__(); self.app = app
        @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
        def onLeScan(self, device, rssi, scanRecord):
            if device.getName() == "Arduino_GCS":
                self.app.connect(device)

    class GattCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]
        def __init__(self, app): super().__init__(); self.app = app
        @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
        def onConnectionStateChange(self, gatt, status, newState):
            if newState == 2:
                Clock.schedule_once(lambda dt: gatt.discoverServices(),1)
                self.app.ble_status = "Verbunden! Suche Services..."
            elif newState == 0:
                self.app.ble_status = "Verbindung getrennt."
        @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
        def onServicesDiscovered(self, gatt, status):
            self.app.ble_status = "Services entdeckt"
            services = gatt.getServices()
            for i in range(services.size()):
                s = services.get(i)
                if "180a" in s.getUuid().toString().lower():
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
                except: pass

class MainApp(App):
    def build(self):
        self.user_data_dir = App.get_running_app().user_data_dir or os.getcwd()
        os.makedirs(self.user_data_dir, exist_ok=True)

        self.root = BoxLayout(orientation="vertical")
        # Dashboard
        self.dashboard = BoxLayout(size_hint_y=0.1)
        self.btn_camera = Button(text="K"); self.btn_camera.bind(on_press=self.show_camera)
        self.btn_gallery = Button(text="G"); self.btn_gallery.bind(on_press=self.show_gallery)
        self.btn_e = Button(text="E"); self.btn_e.bind(on_press=self.show_e)
        self.btn_a = Button(text="A"); self.btn_a.bind(on_press=self.show_a)
        self.ble_display = Label(text="", size_hint_x=0.4)
        for b in [self.btn_camera,self.btn_gallery,self.btn_e,self.btn_a]:
            self.dashboard.add_widget(b)
        self.dashboard.add_widget(self.ble_display)
        self.root.add_widget(self.dashboard)

        self.content = BoxLayout()
        self.root.add_widget(self.content)

        self.arduino_enabled = False
        self.angle = 0
        self.direction = "--"
        self.ble_status = "Nicht verbunden"

        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None

        # Update BLE-Anzeige jede Sekunde
        Clock.schedule_interval(lambda dt: self.update_dashboard(), 1)

        # Berechtigungen Kamera
        if IS_ANDROID:
            request_permissions([Permission.CAMERA], self.permissions_callback)
        else:
            Clock.schedule_once(lambda dt: self.show_camera(),0.1)

        return self.root

    def permissions_callback(self, permissions, results):
        if all(results):
            Clock.schedule_once(lambda dt: self.show_camera(),0.1)
        else:
            self.content.clear_widgets()
            self.content.add_widget(Label(text="Keine Kameraberechtigung!"))

    def update_angle(self, angle):
        self.angle = angle
        self.direction = self.calc_direction(angle)

    def calc_direction(self, angle):
        a = angle % 360
        if a>=337 or a<22: return "Nord"
        if a<67: return "Nordost"
        if a<112: return "Ost"
        if a<157: return "Südost"
        if a<202: return "Süd"
        if a<247: return "Südwest"
        if a<292: return "West"
        return "Nordwest"

    def update_dashboard(self):
        if self.arduino_enabled:
            self.ble_display.text = f"{self.angle}° | {self.direction} | {self.ble_status}"
        else:
            self.ble_display.text = ""

    # ===== Kamera =====
    def show_camera(self,*args):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        try:
            self.camera = Camera(play=True)
            with self.camera.canvas.before:
                PushMatrix()
                self.rot = Rotate(angle=-90, origin=self.camera.center)
            with self.camera.canvas.after:
                PopMatrix()
            self.camera.bind(pos=self.update_rot, size=self.update_rot)
            layout.add_widget(self.camera)
            btn = Button(text="Foto aufnehmen",size_hint_y=0.15)
            btn.bind(on_press=self.take_photo)
            layout.add_widget(btn)
        except Exception as e:
            layout.add_widget(Label(text=f"Kamera konnte nicht gestartet werden:\n{e}"))
        self.content.add_widget(layout)

    def update_rot(self,*args):
        if hasattr(self,'rot'):
            self.rot.origin = self.camera.center

    def take_photo(self, instance):
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
        save = Button(text="Speichern"); repeat = Button(text="Wiederholen")
        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save); btns.add_widget(repeat)
        layout.add_widget(btns)
        self.content.add_widget(layout)

    # ===== Galerie =====
    def show_gallery(self,*args):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])
        for file in files:
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(400))
            lbl = Label(text=file.replace(".png",""), size_hint_y=None, height=dp(30))
            layout.add_widget(lbl)
            img = Image(source=os.path.join(self.user_data_dir, file), size_hint_y=None, height=dp(350), allow_stretch=True, keep_ratio=True)
            img.bind(on_touch_down=lambda inst, touch, f=file: self.open_image(f) if inst.collide_point(*touch.pos) else None)
            layout.add_widget(img)
            grid.add_widget(layout)
        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    def open_image(self, filename):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        img_layout = FloatLayout(size_hint_y=0.8)
        img_path = os.path.join(self.user_data_dir, filename)
        img = Image(source=img_path)
        img_layout.add_widget(img)
        if self.arduino_enabled:
            lbl = Label(text="Norden", color=(1,1,1,1), size_hint=(None,None), pos=(dp(10), dp(10)))
            img_layout.add_widget(lbl)
        layout.add_widget(img_layout)
        bottom = BoxLayout(size_hint_y=0.15)
        name_lbl = Label(text=filename.replace(".png",""))
        info_btn = Button(text="i", size_hint=(None,None), size=(dp(40),dp(40)))
        info_btn.bind(on_press=lambda x: self.show_info(filename))
        bottom.add_widget(name_lbl); bottom.add_widget(info_btn)
        layout.add_widget(bottom)
        self.content.add_widget(layout)

    def show_info(self, filename):
        path = os.path.join(self.user_data_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10)
        box.add_widget(Label(text=f"Name:"))
        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(name_input)
        box.add_widget(Label(text=f"Datum/Uhrzeit: {datetime.fromtimestamp(os.path.getmtime(path))}"))
        save_btn = Button(text="Name speichern")
        save_btn.bind(on_press=lambda x: self.rename_file(filename, name_input.text))
        box.add_widget(save_btn)
        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.confirm_delete(filename))
        box.add_widget(delete_btn)
        popup = Popup(title=f"Info {filename}", content=box, size_hint=(0.8,0.7))
        popup.open()

    def rename_file(self, old_name, new_name):
        old_path = os.path.join(self.user_data_dir, old_name)
        new_path = os.path.join(self.user_data_dir, f"{new_name}.png")
        os.rename(old_path, new_path)
        self.show_gallery()

    def confirm_delete(self, filename):
        path = os.path.join(self.user_data_dir, filename)
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(text="Wirklich löschen?"))
        yes = Button(text="Ja"); no = Button(text="Nein")
        yes.bind(on_press=lambda x: (os.remove(path), self.show_gallery()))
        no.bind(on_press=lambda x: self.show_gallery())
        box.add_widget(yes); box.add_widget(no)
        popup = Popup(title="Sicher?", content=box, size_hint=(0.7,0.4))
        popup.open()

    # ===== A-Seite =====
    def show_a(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical")
        if self.arduino_enabled:
            self.arduino_label = Label(text=f"Winkel: {self.angle}° | Richtung: {self.direction} | {self.ble_status}", size_hint_y=None,height=40)
            vbox.add_widget(self.arduino_label)
            if IS_ANDROID:
                scan_btn = Button(text="Scan starten")
                scan_btn.bind(on_press=self.start_scan)
                vbox.add_widget(scan_btn)
        else:
            vbox.add_widget(Label(text="Sie müssen die Daten erst in den Einstellungen aktivieren"))
        self.content.add_widget(vbox)

    def start_scan(self, *args):
        if not IS_ANDROID: return
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.ble_status = "Bitte Bluetooth aktivieren!"
                return
            self.ble_status = "Scanne..."
            self.scan_cb = BLEScanCallback(self)
            adapter.startLeScan(self.scan_cb)
        except Exception as e:
            self.ble_status = f"Scan Fehler: {str(e)}"

    def connect(self, device):
        adapter = BluetoothAdapter.getDefaultAdapter()
        adapter.stopLeScan(self.scan_cb)
        self.ble_status = f"Verbinde mit {device.getAddress()}..."
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb, 2)

    # ===== E-Seite =====
    def show_e(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical", padding=10, spacing=10)
        h1 = BoxLayout()
        h1.add_widget(Label(text="Mit Arduino"))
        ja = ToggleButton(text="Ja", group="arduino"); nein = ToggleButton(text="Nein", group="arduino", state="down")
        ja.bind(on_press=lambda x: setattr(self,'arduino_enabled', True))
        nein.bind(on_press=lambda x: setattr(self,'arduino_enabled', False))
        h1.add_widget(ja); h1.add_widget(nein)
        vbox.add_widget(h1)
        # Zentrierung
        h2 = BoxLayout(); h2.add_widget(Label(text="Zentrierung"))
        h2.add_widget(ToggleButton(text="Ja", group="zent")); h2.add_widget(ToggleButton(text="Nein", group="zent", state="down"))
        vbox.add_widget(h2)
        # Automatisches Speichern
        h3 = BoxLayout(); h3.add_widget(Label(text="Automatisches Speichern"))
        h3.add_widget(ToggleButton(text="Ja", group="auto")); h3.add_widget(ToggleButton(text="Nein", group="auto", state="down"))
        vbox.add_widget(h3)
        # Mit Winkel
        h4 = BoxLayout(); h4.add_widget(Label(text="Mit Winkel"))
        h4.add_widget(ToggleButton(text="Ja", group="winkel")); h4.add_widget(ToggleButton(text="Nein", group="winkel", state="down"))
        vbox.add_widget(h4)
        self.content.add_widget(vbox)

if __name__ == "__main__":
    MainApp().run()
