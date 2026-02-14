from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
import time

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None

# ───────────── CAMERA SCREEN ─────────────
class CameraScreen(Screen):

    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()

        # Schwarzer Hintergrund
        with layout.canvas:
            Color(0, 0, 0, 1)
            self.bg = Rectangle(size=Window.size, pos=(0, 0))

        Window.bind(size=self.update_bg)

        # Kamera (größer, passt in den gelben Rahmen)
        self.camera = Camera(play=True)
        self.camera.size = (Window.width * 0.9, Window.height * 0.6)
        self.camera.pos = (Window.width * 0.05, Window.height * 0.2)
        layout.add_widget(self.camera)

        # Weißer runder Button rechts mittig
        with layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(120, 120),
                pos=(Window.width - 180, Window.height / 2 - 60)
            )

        # Gelber Rahmen über dem weißen Blatt
        with layout.canvas:
            Color(1, 1, 0, 1)  # Gelb
            self.paper_frame = Line(
                rectangle=(Window.width * 0.05, Window.height * 0.2,
                           Window.width * 0.9, Window.height * 0.6),
                width=2
            )

        layout.bind(on_touch_down=self.take_photo)
        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.size = Window.size
        # Rahmen an neue Fenstergröße anpassen
        self.paper_frame.rectangle = (
            Window.width * 0.05, Window.height * 0.2,
            Window.width * 0.9, Window.height * 0.6
        )
        # Kamera anpassen
        self.camera.size = (Window.width * 0.9, Window.height * 0.6)
        self.camera.pos = (Window.width * 0.05, Window.height * 0.2)
        # Weißer Kreis rechts mittig
        self.capture_circle.pos = (Window.width - 180, Window.height / 2 - 60)

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = f"photo_{int(time.time())}.png"
            self.camera.export_to_png(filename)
            App.get_running_app().last_photo = filename
            self.manager.current = "preview"


# ───────────── PREVIEW SCREEN ─────────────
class PreviewScreen(Screen):

    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()

        # Schwarzer Hintergrund
        with layout.canvas:
            Color(0, 0, 0, 1)
            self.bg = Rectangle(size=Window.size, pos=(0, 0))

        Window.bind(size=self.update_bg)

        # Foto anzeigen
        image = Image(
            source=App.get_running_app().last_photo,
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=True
        )
        image.reload()  # sicherstellen, dass neues Bild geladen wird
        layout.add_widget(image)

        # Wiederholen Button
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        btn_retry.bind(on_press=self.go_back)
        layout.add_widget(btn_retry)

        # Fertig Button (macht nichts)
        btn_done = Button(
            text="Fertig",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.6, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        layout.add_widget(btn_done)

        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.size = Window.size

    def go_back(self, instance):
        self.manager.current = "camera"


# ───────────── MAIN APP ─────────────
class MainApp(App):
    last_photo = None

    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(CameraScreen(name="camera"))
        self.sm.add_widget(PreviewScreen(name="preview"))

        Clock.schedule_once(self.ask_permission, 0.5)

        return self.sm

    def ask_permission(self, dt):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.permission_result)
        else:
            self.permission_result(None, [True])

    def permission_result(self, permissions, results):
        if all(results):
            self.sm.current = "camera"
        else:
            print("Kamera-Berechtigung verweigert")


if __name__ == "__main__":
    MainApp().run()
