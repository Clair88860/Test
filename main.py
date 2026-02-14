from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.core.window import Window
import time

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None


# ───────────── START SCREEN ─────────────
class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()

        with layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size)

        label = Label(
            text="Hallo!\n\nWillkommen zur Kamera-App",
            font_size=50,
            rotation=90,
            size_hint=(None, None),
            size=(600, 400),
            pos_hint={"center_x": 0.5, "center_y": 0.6}
        )
        layout.add_widget(label)

        btn = Button(
            text="Weiter",
            size_hint=(0.3, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.3},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        btn.bind(on_press=self.ask_permission)
        layout.add_widget(btn)

        self.add_widget(layout)

    def ask_permission(self, *_):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.permission_result)
        else:
            self.permission_result(None, [True])

    def permission_result(self, permissions, results):
        if all(results):
            App.get_running_app().store.put("welcome", shown=True)
            self.manager.current = "camera"


# ───────────── CAMERA SCREEN ─────────────
class CameraScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()

        with layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size)

        self.camera = Camera(play=True)
        self.camera.size_hint = (1, 1)
        layout.add_widget(self.camera)

        # Weißer runder Button
        with layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(120, 120),
                pos=(Window.width/2 - 60, 40)
            )

        layout.bind(on_touch_down=self.take_photo)
        self.add_widget(layout)

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x+w and y <= touch.y <= y+h:
            filename = f"photo_{int(time.time())}.png"
            self.camera.export_to_png(filename)
            App.get_running_app().last_photo = filename
            self.manager.current = "preview"


# ───────────── PREVIEW SCREEN ─────────────
class PreviewScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()

        with layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size)

        image = Image(
            source=App.get_running_app().last_photo,
            size_hint=(1, 1)
        )
        layout.add_widget(image)

        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        btn_retry.bind(on_press=lambda *_: self.manager.current = "camera")
        layout.add_widget(btn_retry)

        btn_done = Button(
            text="Fertig",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.6, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        layout.add_widget(btn_done)

        self.add_widget(layout)


# ───────────── MAIN APP ─────────────
class MainApp(App):
    last_photo = None

    def build(self):
        self.store = JsonStore("app_state.json")

        sm = ScreenManager()
        sm.add_widget(StartScreen(name="start"))
        sm.add_widget(CameraScreen(name="camera"))
        sm.add_widget(PreviewScreen(name="preview"))

        if self.store.exists("welcome"):
            sm.current = "camera"
        else:
            sm.current = "start"

        return sm


if __name__ == "__main__":
    MainApp().run()
