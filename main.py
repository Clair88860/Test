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
    # Nummerierung
    # =====================================================

    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    # =====================================================
    # TOPBAR (für alle Seiten außer Kamera)
    # =====================================================

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
            b = Button(
                text=t,
                background_normal="",
                background_color=(0.15, 0.15, 0.15, 1),
                color=(1, 1, 1, 1)
            )
            b.bind(on_press=f)
            self.topbar.add_widget(b)

    # =====================================================
    # KAMERA
    # =====================================================

    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920, 1080))
        self.camera.size_hint = (1, 1)
        self.camera.pos_hint = {"center_x": .5, "center_y": .5}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # =====================================================
    # Runder Kamera Button
    # =====================================================

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

    # =====================================================
    # Kamera anzeigen (Vollbild!)
    # =====================================================

    def show_camera(self, *args):
        self.clear_widgets()

        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(
                text="Kamera Berechtigung fehlt",
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # FOTO
    # =====================================================

    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)

    # =====================================================
    # GALERIE
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1,.92), pos_hint={"y":0})
        grid = GridLayout(cols=3, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        for file in files:
            img = Image(source=os.path.join(self.photos_dir, file))
            img.reload()
            grid.add_widget(img)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # EINSTELLUNGEN (weiter unten)
    # =====================================================

    def show_settings(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(
            orientation="vertical",
            padding=[20, 120, 20, 20],
            spacing=20
        )

        layout.add_widget(Label(
            text="Einstellungen",
            font_size=32,
            size_hint_y=None,
            height=dp(60)
        ))

        self.add_widget(layout)

    # =====================================================
    # ARDUINO
    # =====================================================

    def show_arduino(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=20)
        layout.add_widget(Label(text="Arduino Daten", font_size=28))
        self.add_widget(layout)

    # =====================================================
    # HILFE
    # =====================================================

    def show_help(self, *args):
        self.clear_widgets()
        self.camera.play = False
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe"))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
