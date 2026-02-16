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
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None


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

    # =====================================================
    # TOPBAR
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1})

        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_arduino),
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

    # =====================================================
    # KAMERA
    # =====================================================

    def build_camera(self):
        self.camera = Camera(play=False)
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"x": 0, "y": 0}

    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            pos_hint={"center_x": .5, "y": .05},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture.size, pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    def take_photo(self, instance):
        number = len([f for f in os.listdir(self.photos_dir) if f.endswith(".png")]) + 1
        path = os.path.join(self.photos_dir, f"{number:04d}.png")
        self.camera.export_to_png(path)
        self.show_preview(path)

    # =====================================================
    # FOTO VORSCHAU
    # =====================================================

    def show_preview(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")

        img = Image(source=path)
        layout.add_widget(img)

        btn_row = BoxLayout(size_hint_y=.15)

        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")

        save.bind(on_press=lambda x: self.show_camera())
        repeat.bind(on_press=lambda x: self.show_camera())

        btn_row.add_widget(save)
        btn_row.add_widget(repeat)

        layout.add_widget(btn_row)
        self.add_widget(layout)

    # =====================================================
    # GALERIE
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1, .92))
        grid = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        for file in files:
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(300))

            name = Label(text=file.replace(".png", ""), size_hint_y=.15)
            img = Image(source=os.path.join(self.photos_dir, file))

            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_single(f) if inst.collide_point(*touch.pos) else None)

            box.add_widget(name)
            box.add_widget(img)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    def open_single(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        path = os.path.join(self.photos_dir, filename)
        layout = BoxLayout(orientation="vertical")

        img = Image(source=path)
        layout.add_widget(img)

        back = Button(text="Zurück", size_hint_y=.1)
        back.bind(on_press=self.show_gallery)
        layout.add_widget(back)

        self.add_widget(layout)

    # =====================================================
    # EINSTELLUNGEN
    # =====================================================

    def show_settings(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)

        def toggle_row(text, key):
            row = BoxLayout(size_hint_y=None, height=dp(50))
            label = Label(text=text)

            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(70),dp(40)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(70),dp(40)))

            value = self.store.get(key)["value"] if self.store.exists(key) else False

            def update(v):
                btn_ja.background_color = (0,0.5,0,1) if v else (1,1,1,1)
                btn_nein.background_color = (0,0.5,0,1) if not v else (1,1,1,1)

            update(value)

            btn_ja.bind(on_press=lambda x: [self.store.put(key,value=True), update(True)])
            btn_nein.bind(on_press=lambda x: [self.store.put(key,value=False), update(False)])

            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row

        layout.add_widget(toggle_row("Mit Arduino", "arduino"))
        layout.add_widget(toggle_row("Mit Entzerrung", "entzerrung"))
        layout.add_widget(toggle_row("Automatisches Speichern", "auto"))
        layout.add_widget(toggle_row("Mit Winkel", "winkel"))

        self.add_widget(layout)

    # =====================================================
    # ARDUINO (stabiler Scan)
    # =====================================================

    def show_arduino(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.status_lbl = Label(text="Bereit")
        scan_btn = Button(text="Scan starten")

        layout.add_widget(self.status_lbl)
        layout.add_widget(scan_btn)
        self.add_widget(layout)

        if platform != "android":
            self.status_lbl.text = "Nur Android"
            return

        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            adapter = BluetoothAdapter.getDefaultAdapter()

            def start_scan(instance):
                if not adapter or not adapter.isEnabled():
                    self.status_lbl.text = "Bluetooth aktivieren"
                    return
                self.status_lbl.text = "Scan läuft..."

            scan_btn.bind(on_press=start_scan)

        except Exception as e:
            self.status_lbl.text = f"Fehler: {e}"


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
