from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
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
        self.layout = layout  # speichern, um später Hilfe anzuzeigen

        # Schwarzer Hintergrund
        with layout.canvas:
            Color(0, 0, 0, 1)
            self.bg = Rectangle(size=Window.size, pos=(0, 0))

        Window.bind(size=self.update_bg)

        # Kamera vergrößert (etwas breiter + länger)
        self.camera = Camera(play=True)
        cam_width = Window.width + 50
        cam_height = Window.height + 50
        self.camera.size = (cam_width, cam_height)
        self.camera.pos = (-25, -25)  # mittig verschieben
        layout.add_widget(self.camera)

        # Weißer runder Button rechts mittig
        with layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(120, 120),
                pos=(Window.width - 180, Window.height / 2 - 60)
            )

        # Hilfe-Button links oben
        btn_help = Button(
            text="Hilfe",
            size_hint=(0.2, 0.1),
            pos_hint={"x": 0.02, "y": 0.88},
            background_color=(0.8, 0.8, 0.8, 1)
        )
        btn_help.bind(on_press=self.show_help)
        layout.add_widget(btn_help)

        layout.bind(on_touch_down=self.take_photo)
        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.size = Window.size
        # Kamera an neue Fenstergröße anpassen
        cam_width = Window.width + 50
        cam_height = Window.height + 50
        self.camera.size = (cam_width, cam_height)
        self.camera.pos = (-25, -25)
        # Weißer Kreis rechts mittig
        self.capture_circle.pos = (Window.width - 180, Window.height / 2 - 60)

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size
        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = os.path.join(App.get_running_app().user_data_dir,
                                    f"photo_{int(time.time())}.png")
            self.camera.export_to_png(filename)
            App.get_running_app().last_photo = filename
            self.manager.current = "preview"

    def show_help(self, instance):
        self.layout.clear_widgets()
        with self.layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size, pos=(0, 0))
        # Hilfe Text
        lbl = Label(
            text="Hilfe",
            font_size=50,
            color=(1, 1, 1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.6}
        )
        self.layout.add_widget(lbl)
        # K-Button unten, zurück zur Kamera
        btn_back = Button(
            text="K",
            size_hint=(0.2, 0.1),
            pos_hint={"center_x": 0.5, "y": 0.05},
            background_color=(0.8, 0.8, 0.8, 1)
        )
        btn_back.bind(on_press=self.back_to_camera)
        self.layout.add_widget(btn_back)

    def back_to_camera(self, instance):
        self.layout.clear_widgets()
        self.on_enter()


# ───────────── PREVIEW SCREEN ─────────────
class PreviewScreen(Screen):

    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()

        # Schwarzer Hintergrund
        with layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size, pos=(0, 0))

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

        # Wiederholen Button
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        btn_retry.bind(on_press=self.go_back)
        layout.add_widget(btn_retry)

        # Fertig Button
        btn_done = Button(
            text="Fertig",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.6, "y": 0.05},
            background_color=(0.2, 0.2, 0.2, 1)
        )
        layout.add_widget(btn_done)

        self.add_widget(layout)

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
