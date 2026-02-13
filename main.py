from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse
from kivy.uix.widget import Widget
import time

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)
TEXT_COLOR = (1, 1, 1, 1)


# ───────────── Weißer Kreis Button ─────────────
class CircleButton(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (150, 150)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

        with self.canvas:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(pos=self.pos, size=self.size)

    def update_canvas(self, *args):
        self.circle.pos = self.pos
        self.circle.size = self.size


# ───────────── Kamera Screen ─────────────
class CameraScreen(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        self.camera = Camera(index=0, resolution=(640, 480), play=True)
        self.add_widget(self.camera)

        bottom = BoxLayout(size_hint=(1, 0.25))
        bottom.add_widget(Label())

        self.capture_btn = CircleButton()
        self.capture_btn.bind(on_touch_down=self.capture_image)
        bottom.add_widget(self.capture_btn)

        bottom.add_widget(Label())
        self.add_widget(bottom)

    def capture_image(self, instance, touch):
        if instance.collide_point(*touch.pos):
            filename = f"/storage/emulated/0/DCIM/photo_{int(time.time())}.png"
            self.camera.export_to_png(filename)
            print("Foto gespeichert:", filename)


# ───────────── Willkommen Screen ─────────────
class WelcomeScreen(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical", padding=40, spacing=40)
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        self.add_widget(Label(size_hint=(1, 0.2)))

        text = Label(
            text="Herzlich Willkommen!\n\n"
                 "Vielen Dank, dass Sie diese App ausprobieren.",
            color=TEXT_COLOR,
            font_size=48,
            halign="center",
            valign="middle",
            size_hint=(1, 0.4)
        )
        text.bind(size=text.setter("text_size"))
        self.add_widget(text)

        btn = Button(
            text="Weiter",
            font_size=42,
            size_hint=(0.6, 0.18),
            pos_hint={"center_x": 0.5},
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
            self.app.root = CameraScreen(self.app)


# ───────────── Main App ─────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        if not self.store.exists("welcome"):
            return WelcomeScreen(self)
        else:
            return CameraScreen(self)


if __name__ == "__main__":
    MainApp().run()
