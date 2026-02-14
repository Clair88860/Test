from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
import time

# Android Permission
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None


DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)


# ───────────────── START SCREEN ─────────────────
class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()
        Window.clearcolor = DARK_BLUE_BG

        label = Label(
            text="Hallo!\n\nWillkommen zur Kamera-App",
            font_size=40,
            size_hint=(None, None),
            size=(Window.width * 0.8, 200),
            pos=(Window.width * 0.1, Window.height * 0.6),
            halign="center"
        )
        label.bind(size=label.setter("text_size"))
        layout.add_widget(label)

        btn = Button(
            text="Weiter",
            size_hint=(None, None),
            size=(250, 100),
            pos=(Window.width/2 - 125, Window.height * 0.35)
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
            app = App.get_running_app()
            app.store.put("welcome", shown=True)
            Clock.schedule_once(lambda dt: self.go_camera(), 0)

    def go_camera(self):
        self.manager.current = "camera"


# ───────────────── CAMERA SCREEN ─────────────────
class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        self.camera = Camera(play=True, index=0)
        self.camera.size_hint = (None, None)
        self.camera.size = (Window.width, Window.height)
        self.camera.pos = (0, 0)
        layout.add_widget(self.camera)

        with layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_btn = Ellipse(
                size=(90, 90),
                pos=(Window.width/2 - 45, 40)
            )

        layout.bind(on_touch_down=self.capture_image)

        self.add_widget(layout)

    def capture_image(self, instance, touch):
        x, y = self.capture_btn.pos
        w, h = self.capture_btn.size

        if x <= touch.x <= x+w and y <= touch.y <= y+h:
            filename = f"/storage/emulated/0/DCIM/photo_{int(time.time())}.png"
            self.camera.export_to_png(filename)
            print("Foto gespeichert:", filename)


# ───────────────── APP ─────────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        sm = ScreenManager()

        sm.add_widget(StartScreen(name="start"))
        sm.add_widget(CameraScreen(name="camera"))

        if self.store.exists("welcome"):
            sm.current = "camera"
        else:
            sm.current = "start"

        return sm


if __name__ == "__main__":
    MainApp().run()
