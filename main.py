import os
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Ellipse
from kivy.storage.jsonstore import JsonStore

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # TOP BAR
        topbar = BoxLayout(size_hint=(1, 0.1))

        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra)
        ]:
            btn = Button(text=text)
            btn.bind(on_press=func)
            topbar.add_widget(btn)

        self.add_widget(topbar)

        # CONTENT
        self.content = FloatLayout()
        self.add_widget(self.content)

        # BOTTOM
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()

        # ✅ Beim Start einmal prüfen
        if self.camera_available():
            self.show_camera()
        else:
            self.show_help()

    # ================= SETTINGS =================

    def get_setting(self, key):
        if self.store.exists(key):
            return self.store.get(key)["value"]
        return "Nein"

    def set_setting(self, key, value):
        self.store.put(key, value=value)

    # ================= CAMERA CHECK =================

    def camera_available(self):
        try:
            cam = Camera()
            cam.play = False
            return True
        except:
            return False

    # ================= CAMERA BUTTON =================

    def create_capture_button(self):
        self.capture_button = Button(
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            background_normal="",
            background_color=(0, 0, 0, 0),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        with self.capture_button.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture_button.size,
                                  pos=self.capture_button.pos)

        self.capture_button.bind(pos=self.update_circle,
                                 size=self.update_circle)
        self.capture_button.bind(on_press=self.take_photo)

        self.bottom.add_widget(self.capture_button)

    def update_circle(self, *args):
        self.circle.pos = self.capture_button.pos
        self.circle.size = self.capture_button.size

    # ================= CAMERA =================

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        self.camera = Camera(play=True)
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        # ✅ Drehung aktivieren
        Window.bind(on_resize=self.update_orientation)
        self.update_orientation()

    def update_orientation(self, *args):
        if hasattr(self, "camera"):
            if Window.height > Window.width:
                self.camera.rotation = -90
            else:
                self.camera.rotation = 0

    # ================= REST BLEIBT 1:1 =================
