from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
import time

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)
TEXT_COLOR = (1, 1, 1, 1)


# ───────────── Willkommen Screen ─────────────
class WelcomeScreen(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        text = Label(
            text="Herzlich Willkommen!\n\nVielen Dank, dass Sie diese App ausprobieren.",
            font_size=40,
            color=TEXT_COLOR,
            halign="center",
            valign="middle",
            size_hint=(0.9, 0.5),
            pos_hint={"center_x": 0.5, "center_y": 0.65}
        )
        text.bind(size=text.setter("text_size"))
        self.add_widget(text)

        btn = Button(
            text="Weiter",
            font_size=36,
            size_hint=(0.5, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.3},
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )
        btn.bind(on_press=self.ask_permission)
        self.add_widget(btn)

    def ask_permission(self, instance):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.permission_result)
        else:
            self.permission_result(None, [True])

    def permission_result(self, permissions, results):
        if all(results):
            self.app.store.put("welcome", shown=True)
            self.app.show_camera()


# ───────────── Kamera Screen ─────────────
class CameraScreen(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        # Kamera Vollbild
        self.camera = Camera(play=True, index=0)
        self.camera.size_hint = (1, 1)
        self.add_widget(self.camera)

        # Roter Punkt (immer mittig)
        with self.canvas:
            Color(1, 0, 0, 1)
            self.dot = Ellipse(size=(15, 15))

        self.bind(size=self.update_dot, pos=self.update_dot)

        # Weißer Capture Button unten mittig
        with self.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(size=(80, 80))

        self.bind(size=self.update_button, pos=self.update_button)

        self.bind(on_touch_down=self.capture_image)

    def update_dot(self, *args):
        self.dot.pos = (
            self.center_x - 7.5,
            self.center_y - 7.5
        )

    def update_button(self, *args):
        self.capture_circle.pos = (
            self.center_x - 40,
            40
        )

    def capture_image(self, instance, touch):
        # Prüfen ob Touch im Kreis
        bx, by = self.capture_circle.pos
        bw, bh = self.capture_circle.size

        if bx <= touch.x <= bx + bw and by <= touch.y <= by + bh:
            filename = f"/storage/emulated/0/DCIM/photo_{int(time.time())}.png"
            self.camera.export_to_png(filename)
            print("Foto gespeichert:", filename)


# ───────────── App ─────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        if not self.store.exists("welcome"):
            return WelcomeScreen(self)
        else:
            return CameraScreen(self)

    def show_camera(self):
        self.root = CameraScreen(self)


if __name__ == "__main__":
    MainApp().run()
