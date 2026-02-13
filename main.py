from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)
TEXT_COLOR = (1, 1, 1, 1)


# ───────────── Willkommen (nur einmal) ─────────────
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
            font_size=40,
            halign="center",
            valign="middle",
            size_hint=(1, 0.4)
        )
        text.bind(size=text.setter("text_size"))
        self.add_widget(text)

        btn = Button(
            text="Weiter",
            font_size=36,
            size_hint=(0.5, 0.15),
            pos_hint={"center_x": 0.5},
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )
        btn.bind(on_press=self.ask_permission)
        self.add_widget(btn)

    def ask_permission(self, instance):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.after_permission)
        else:
            self.after_permission(None, [True])

    def after_permission(self, permissions, results):
        if all(results):
            self.app.store.put("welcome", shown=True)
            self.app.show_camera()


# ───────────── Kamera Screen ─────────────
class CameraScreen(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        self.camera = Camera(
            resolution=(640, 480),
            play=True
        )

        close_btn = Button(
            text="Beenden",
            size_hint=(1, 0.15),
            font_size=30,
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )

        close_btn.bind(on_press=self.stop_camera)

        self.add_widget(self.camera)
        self.add_widget(close_btn)

    def stop_camera(self, instance):
        self.camera.play = False
        self.app.show_camera()  # startet neu


# ───────────── App ─────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        if not self.store.exists("welcome"):
            return WelcomeScreen(self)
        else:
            return CameraScreen(self)

    def show_camera(self):
        self.root.clear_widgets()
        self.root.add_widget(CameraScreen(self))


if __name__ == "__main__":
    MainApp().run()
