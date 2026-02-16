import os
import struct
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None


# ==========================================================
# DASHBOARD
# ==========================================================

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

    # ======================================================
    # TOPBAR (immer sichtbar)
    # ======================================================

    def build_topbar(self):
        self.topbar = BoxLayout(
            size_hint=(1, .08),
            pos_hint={"top": 1},
            spacing=5,
            padding=5
        )

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

    # ======================================================
    # KAMERA
    # ======================================================

    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920, 1080))
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"center_x": .5, "y": 0}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(100), dp(100)),
            pos_hint={"center_x": .5, "y": .05},
            background_normal="",
            background_color=(0, 0, 0, 0)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.outer_circle = Ellipse(size=self.capture.size,
                                        pos=self.capture.pos)

            Color(0.9, 0.9, 0.9, 1)
            self.inner_circle = Ellipse(
                size=(dp(75), dp(75)),
                pos=(self.capture.x + dp(12.5),
                     self.capture.y + dp(12.5))
            )

        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size
        self.inner_circle.pos = (
            self.capture.x + dp(12.5),
            self.capture.y + dp(12.5)
        )

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(text="Kamera Berechtigung fehlt",
                                  pos_hint={"center_x": .5, "center_y": .5}))
            return

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    def take_photo(self, instance):
        number = len([f for f in os.listdir(self.photos_dir) if f.endswith(".png")]) + 1
        path = os.path.join(self.photos_dir, f"{number:04d}.png")
        self.camera.export_to_png(path)

    # ======================================================
    # GALERIE
    # ======================================================

    def show_gallery(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1, .92), pos_hint={"y": 0})
        grid = GridLayout(cols=3, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in os.listdir(self.photos_dir):
            if file.endswith(".png"):
                img = Image(source=os.path.join(self.photos_dir, file))
                grid.add_widget(img)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # ======================================================
    # EINSTELLUNGEN
    # ======================================================

    def show_settings(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(
            orientation="vertical",
            padding=[20, 120, 20, 20]
        )

        layout.add_widget(Label(text="Einstellungen", font_size=32))
        self.add_widget(layout)

    # ======================================================
    # ARDUINO BLE
    # ======================================================

    def show_arduino(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.angle_lbl = Label(text="0°", font_size=80, size_hint_y=0.4)
        self.scan_btn = Button(text="Scan starten", size_hint_y=0.15)
        self.log_lbl = Label(text="Bereit\n", size_hint_y=0.45)

        layout.add_widget(self.angle_lbl)
        layout.add_widget(self.scan_btn)
        layout.add_widget(self.log_lbl)

        self.add_widget(layout)

        if platform != "android":
            self.log_lbl.text += "Nur auf Android verfügbar\n"
            return

        from jnius import autoclass, PythonJavaClass, java_method
        BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")

        adapter = BluetoothAdapter.getDefaultAdapter()

        class ScanCallback(PythonJavaClass):
            __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]

            @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
            def onLeScan(self, device, rssi, scanRecord):
                if device.getName() == "Arduino_GCS":
                    Clock.schedule_once(lambda dt:
                        setattr(self.angle_lbl, "text", "Arduino gefunden"))

        scan_cb = ScanCallback()

        def start_scan(instance):
            if not adapter or not adapter.isEnabled():
                self.log_lbl.text += "Bluetooth aktivieren!\n"
                return
            self.log_lbl.text += "Scanne...\n"
            adapter.startLeScan(scan_cb)

        self.scan_btn.bind(on_press=start_scan)

    # ======================================================
    # HILFE
    # ======================================================

    def show_help(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe"))


# ==========================================================
# APP START
# ==========================================================

class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
