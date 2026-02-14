from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
import time
import os

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


APP_DIR = "/storage/emulated/0/Documents/MyCameraApp"
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)


# ───────────── START SCREEN ─────────────
class StartScreen(FloatLayout):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.add_widget(Label(
            text="Willkommen",
            font_size=40,
            pos=(Window.width/2 - 150, Window.height * 0.75),
            size_hint=(None, None)
        ))

        self.cam_btn = Button(
            text="Kamera Berechtigung",
            size=(400, 90),
            pos=(Window.width/2 - 200, Window.height * 0.55),
            size_hint=(None, None)
        )
        self.cam_btn.bind(on_press=self.ask_camera)
        self.add_widget(self.cam_btn)

        self.doc_btn = Button(
            text="Dokumente Berechtigung",
            size=(400, 90),
            pos=(Window.width/2 - 200, Window.height * 0.40),
            size_hint=(None, None)
        )
        self.doc_btn.bind(on_press=self.ask_storage)
        self.add_widget(self.doc_btn)

        self.next_btn = Button(
            text="Weiter",
            size=(300, 90),
            pos=(Window.width/2 - 150, Window.height * 0.20),
            size_hint=(None, None)
        )
        self.next_btn.bind(on_press=lambda x: self.app.show_camera())
        self.add_widget(self.next_btn)

    def ask_camera(self, _):
        if request_permissions:
            request_permissions([Permission.CAMERA], lambda *a: None)

    def ask_storage(self, _):
        if request_permissions:
            request_permissions(
                [Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE],
                lambda *a: None
            )


# ───────────── CAMERA SCREEN ─────────────
class CameraScreen(FloatLayout):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.camera = Camera(play=True)
        self.camera.size = (Window.width, Window.height)
        self.camera.pos = (0, 0)
        self.add_widget(self.camera)

        with self.canvas:
            Color(1, 1, 1, 1)
            self.capture_btn = Ellipse(
                size=(90, 90),
                pos=(Window.width/2 - 45, 40)
            )

        self.bind(on_touch_down=self.capture)

    def capture(self, _, touch):
        bx, by = self.capture_btn.pos
        bw, bh = self.capture_btn.size

        if bx <= touch.x <= bx + bw and by <= touch.y <= by + bh:
            self.filename = f"/storage/emulated/0/DCIM/tmp_{int(time.time())}.png"
            self.camera.export_to_png(self.filename)
            Clock.schedule_once(lambda dt: self.app.show_preview(self.filename), 0)


# ───────────── PREVIEW SCREEN ─────────────
class PreviewScreen(FloatLayout):
    def __init__(self, app, image_path):
        super().__init__()
        self.app = app
        self.image_path = image_path

        img = Image(
            source=image_path,
            size=(Window.width, Window.height * 0.75),
            pos=(0, Window.height * 0.25),
            allow_stretch=True
        )
        self.add_widget(img)

        save_btn = Button(
            text="Speichern",
            size=(300, 90),
            pos=(Window.width * 0.1, 60),
            size_hint=(None, None)
        )
        save_btn.bind(on_press=self.save)
        self.add_widget(save_btn)

        repeat_btn = Button(
            text="Wiederholen",
            size=(300, 90),
            pos=(Window.width * 0.55, 60),
            size_hint=(None, None)
        )
        repeat_btn.bind(on_press=lambda x: self.app.show_camera())
        self.add_widget(repeat_btn)

    def save(self, _):
        target = os.path.join(APP_DIR, f"photo_{int(time.time())}.png")
        os.rename(self.image_path, target)
        self.app.show_camera()


# ───────────── APP ─────────────
class MainApp(App):
    def build(self):
        return StartScreen(self)

    def show_camera(self):
        self.root = CameraScreen(self)

    def show_preview(self, path):
        self.root = PreviewScreen(self, path)


if __name__ == "__main__":
    MainApp().run()
