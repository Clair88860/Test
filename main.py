from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
import time
import os

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

        # Kamera (groß, füllt ganzen Bildschirm)
        self.camera = Camera(play=True)
        self.camera.size = Window.size
        self.camera.pos = (0, 0)
        layout.add_widget(self.camera)

        # Weißer runder Button rechts mittig
        with layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(120, 120),
                pos=(Window.width - 180, Window.height / 2 - 60)
            )

        layout.bind(on_touch_down=self.take_photo)
        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.size = Window.size
        # Kamera an neue Fenstergröße anpassen
        self.camera.size = Window.size
        self.camera.pos = (0, 0)
        # Weißer Kreis rechts mittig
        self.capture_circle.pos = (Window.width - 180, Window.height / 2 - 60)

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = f"photo_{int(time.time())}.png"
            # Speichern im aktuellen Verzeichnis
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
        photo_path = App.get_running_app().last_photo
        if photo_path and os.path.exists(photo_path):
            image = Image(
                source=photo_path,
                size_hint=(1, 1),
                allow_stretch=True,
                keep_ratio=True
            )
            layout.add_widget(image)
        else:
            # Falls Datei fehlt, schwarzen Hintergrund anzeigen
            pass

        # Wiederholen Button
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        btn_retry.bind(on_press=self.go_back)
        layout.add_widget(btn_retry)

        # Fertig Button (macht aktuell nichts)
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
