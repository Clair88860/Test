import os
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock

# BLE A-Seite Imports
from kivy.utils import platform
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

# BLE Callbacks für A-Seite
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

class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app
    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2: # STATE_CONNECTED
            self.app.log("Verbunden! Suche Services...")
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1.0)
        elif newState == 0: # STATE_DISCONNECTED
            self.app.log("Verbindung getrennt.")
    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")
        services = gatt.getServices()
        for i in range(services.size()):
            s = services.get(i)
            s_uuid = s.getUuid().toString().lower()
            if "180a" in s_uuid:
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
                import struct
                angle = struct.unpack('<h', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_data(angle))
            except Exception as e:
                self.app.log(f"Fehler: {str(e)}")


# =====================================================
# Dashboard (Kamera, Galerie, E-, A-, Help-Seite)
# =====================================================
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore("settings.json")
        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    # =====================================================
    # Topbar
    # =====================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1})
        for t, f in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_arduino)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

    # =====================================================
    # Kamera
    # =====================================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920,1080))
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"x":0,"y":0}
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # =====================================================
    # Kamera Button
    # =====================================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None), size=(dp(80),dp(80)),
                              pos_hint={"center_x":.5,"y":.03},
                              background_normal="", background_color=(1,1,1,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.circle = Ellipse(size=self.capture.size, pos=self.capture.pos)
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    # =====================================================
    # Kamera anzeigen
    # =====================================================
    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if self.store.exists("camera_permission") and self.store.get("camera_permission")["value"]:
            self.camera.play = True
            self.add_widget(self.camera)
            self.add_widget(self.capture)
        else:
            # Keine Berechtigung
            lbl = Label(text="Berechtigung fehlt", pos_hint={"center_x":.5,"center_y":.5})
            self.add_widget(lbl)

    # =====================================================
    # Foto aufnehmen
    # =====================================================
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number+".png")
        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False
        if auto:
            self.camera.export_to_png(path)
        else:
            content = BoxLayout(orientation="vertical", spacing=10)
            content.add_widget(Label(text="Foto speichern?"))
            btns = BoxLayout()
            save = Button(text="Speichern")
            repeat = Button(text="Wiederholen")
            save.bind(on_press=lambda x: [self.camera.export_to_png(path), popup.dismiss()])
            repeat.bind(on_press=lambda x: popup.dismiss())
            btns.add_widget(save)
            btns.add_widget(repeat)
            content.add_widget(btns)
            popup = Popup(title="Speichern", content=content, size_hint=(.7,.4))
            popup.open()

    # =====================================================
    # Galerie
    # =====================================================
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        scroll = ScrollView(size_hint=(1,.92))
        grid = GridLayout(cols=3, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        for file in files:
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(160))
            num = Label(text=file.replace(".png",""), size_hint_y=.2)
            layout.add_widget(num)
            img = Image(source=os.path.join(self.photos_dir,file))
            img.reload()
            img.bind(on_touch_down=lambda inst,touch,f=file:self.open_image(f) if inst.collide_point(*touch.pos) else None)
            layout.add_widget(img)
            grid.add_widget(layout)
        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # Einzelbild
    # =====================================================
    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)
        path = os.path.join(self.photos_dir, filename)
        layout = BoxLayout(orientation="vertical")
        img_layout = FloatLayout(size_hint_y=.8)
        img = Image(source=path)
        img_layout.add_widget(img)
        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            north = Label(text="Norden", pos_hint={"right":.95,"top":.98})
            img_layout.add_widget(north)
        layout.add_widget(img_layout)
        bottom = BoxLayout(size_hint_y=.15)
        number_label = Label(text=filename.replace(".png",""))
        info = Button(text="i", size_hint=(None,None), size=(dp(40),dp(40)), background_normal="", background_color=(0,0,0,0))
        info.bind(on_press=lambda x:self.image_info(filename))
        bottom.add_widget(number_label)
        bottom.add_widget(info)
        layout.add_widget(bottom)
        self.add_widget(layout)

    # =====================================================
    # Bildinfo Popup
    # =====================================================
    def image_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        box = BoxLayout(orientation="vertical", spacing=10)
        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(name_input)
        box.add_widget(Label(text=str(dt)))
        save_name = Button(text="Name speichern")
        save_name.bind(on_press=lambda x:self.rename_file(filename,name_input.text))
        box.add_widget(save_name)
        delete = Button(text="Foto löschen")
        delete.bind(on_press=lambda x:self.delete_file(filename))
        box.add_widget(delete)
        popup = Popup(title="Info", content=box, size_hint=(.8,.7))
        popup.open()

    def rename_file(self, old, new):
        old_path = os.path.join(self.photos_dir, old)
        new_path = os.path.join(self.photos_dir, new+".png")
        if not os.path.exists(new_path):
            os.rename(old_path,new_path)
        self.show_gallery()

    def delete_file(self, filename):
        path = os.path.join(self.photos_dir, filename)
        if os.path.exists(path):
            os.remove(path)
        self.show_gallery()

    # =====================================================
    # Einstellungen E-Seite
    # =====================================================
    def show_settings(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        layout.add_widget(Label(text="Einstellungen", font_size=36))
        def create_toggle_row(text,key):
            row = BoxLayout(size_hint_y=None, height=dp(50))
            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(70),dp(40)))
            btn_nein=Button(text="Nein", size_hint=(None,None), size=(dp(70),dp(40)))
            val = self.store.get(key)["value"] if self.store.exists(key) else False
            def update(sel):
                if sel:
                    btn_ja.background_color=(0,0.5,0,1)
                    btn_nein.background_color=(1,1,1,1)
                else:
                    btn_nein.background_color=(0,0.5,0,1)
                    btn_ja.background_color=(1,1,1,1)
            update(val)
            btn_ja.bind(on_press=lambda x:[self.store.put(key,value=True),update(True)])
            btn_nein.bind(on_press=lambda x:[self.store.put(key,value=False),update(False)])
            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row
        layout.add_widget(create_toggle_row("Mit Arduino Daten","arduino"))
        layout.add_widget(create_toggle_row("Mit Winkel","winkel"))
        layout.add_widget(create_toggle_row("Automatisches Speichern","auto"))
        layout.add_widget(Label(text="Hinweis: Arduino aktiviert Norden Anzeige",color=(0,0,0,1)))
        layout.add_widget(Label(text="Hinweis: Auto Speichern überspringt Abfrage",color=(0,0,0,1)))
        self.add_widget(layout)

    # =====================================================
    # A-Seite (BLE)
    # =====================================================
    def show_arduino(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation='vertical',padding=20,spacing=10)
        layout.add_widget(Label(text="Arduino Daten",font_size=28))
        App.get_running_app().root = layout

    # =====================================================
    # Hilfe
    # =====================================================
    def show_help(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe"))

# =====================================================
# App
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()


if __name__=="__main__":
    MainApp().run()
