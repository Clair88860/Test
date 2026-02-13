from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


# ───────────── Design ─────────────
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
        btn.bind(on_press=self.go_next)
        self.add_widget(btn)

    def go_next(self, instance):
        self.app.store.put("welcome", shown=True)
        self.app.show_arduino_question()


# ───────────── Arduino Frage ─────────────
class ArduinoScreen(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical", padding=40, spacing=30)
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        question = Label(
            text="Möchten Sie die App\nmit dem Arduino durchführen?",
            color=TEXT_COLOR,
            font_size=42,
            halign="center",
            valign="middle",
            size_hint=(1, 0.4)
        )
        question.bind(size=question.setter("text_size"))
        self.add_widget(question)

        row = BoxLayout(orientation="horizontal", spacing=40, size_hint=(1, 0.2))

        btn_yes = Button(text="Ja", font_size=36,
                         background_color=DARK_BLUE_BG,
                         color=TEXT_COLOR)

        btn_no = Button(text="Nein", font_size=36,
                        background_color=DARK_BLUE_BG,
                        color=TEXT_COLOR)

        btn_yes.bind(on_press=self.open_camera)
        btn_no.bind(on_press=self.open_camera)

        row.add_widget(btn_yes)
        row.add_widget(btn_no)
        self.add_widget(row)

    def open_camera(self, instance):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.after_permission)
        else:
            self.start_camera()

    def after_permission(self, permissions, results):
        if all(results):
            self.start_camera()

    def start_camera(self):
        self.clear_widgets()

        cam = Camera(
            resolution=(640, 480),
            play=True
        )

        close_btn = Button(
            text="Zurück",
            size_hint=(1, 0.15),
            font_size=32,
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(cam)
        layout.add_widget(close_btn)

        close_btn.bind(on_press=lambda x: self.app.show_arduino_question())

        self.add_widget(layout)


# ───────────── App ─────────────
class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        if not self.store.exists("welcome"):
            return WelcomeScreen(self)
        else:
            return ArduinoScreen(self)

    def show_arduino_question(self):
        self.root.clear_widgets()
        self.root.add_widget(ArduinoScreen(self))


if __name__ == "__main__":
    MainApp().run()
