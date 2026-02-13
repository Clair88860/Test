from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from jnius import autoclass

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


# ───────────── Design ─────────────
DARK_BLUE_BG = (0.02, 0.1, 0.3, 1)
TEXT_COLOR = (1, 1, 1, 1)


class WelcomeScreen(BoxLayout):
    """Wird nur EINMAL angezeigt"""
    def __init__(self, app):
        super().__init__(orientation="vertical", padding=40, spacing=40)
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        # Abstand nach oben
        self.add_widget(Label(size_hint=(1, 0.2)))

        text = Label(
            text="Herzlich Willkommen!\n\n"
                 "Vielen Dank, dass Sie diese App ausprobieren.\n"
                 "...",
            color=TEXT_COLOR,
            font_size=56,
            halign="center",
            valign="middle",
            size_hint=(1, 0.4)
        )
        text.bind(size=text.setter("text_size"))
        self.add_widget(text)

        btn = Button(
            text="Weiter",
            font_size=42,
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


class ArduinoScreen(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical", padding=40, spacing=30)
        self.app = app
        Window.clearcolor = DARK_BLUE_BG

        # ── Obere Leiste ──
        top_bar = BoxLayout(orientation="horizontal", size_hint=(1, 0.15))
        top_bar.add_widget(Label())

        help_btn = Button(
            text="?",
            font_size=48,
            size_hint=(None, None),
            size=(100, 100),
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )
        help_btn.bind(on_press=self.show_help)
        top_bar.add_widget(help_btn)
        self.add_widget(top_bar)

        # ── Arduino Frage (HALB SO GROß) ──
        question = Label(
            text="Möchten Sie die App\nmit dem Arduino durchführen?",
            color=TEXT_COLOR,
            font_size=42,   # ⬅️ halb so groß
            halign="center",
            valign="middle",
            size_hint=(1, 0.45)
        )
        question.bind(size=question.setter("text_size"))
        self.add_widget(question)

        # ── Buttons ──
        row = BoxLayout(orientation="horizontal", spacing=40, size_hint=(1, 0.25))

        btn_yes = Button(
            text="Ja",
            font_size=36,
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )
        btn_no = Button(
            text="Nein",
            font_size=36,
            background_color=DARK_BLUE_BG,
            color=TEXT_COLOR
        )

        btn_yes.bind(on_press=self.open_camera)
        btn_no.bind(on_press=self.open_camera)

        row.add_widget(btn_yes)
        row.add_widget(btn_no)
        self.add_widget(row)

    def show_help(self, instance):
        content = Label(
            text="Bei Fragen können Sie uns\n"
                 "einfach eine E-Mail schicken.",
            font_size=32,
            halign="center",
            valign="middle"
        )
        content.bind(size=content.setter("text_size"))

        Popup(
            title="Hilfe",
            content=content,
            size_hint=(0.7, 0.35)
        ).open()

    def open_camera(self, instance):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.after_permission)
        else:
            self.start_camera()

    def after_permission(self, permissions, results):
        if all(results):
            self.start_camera()

    def start_camera(self):
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        MediaStore = autoclass("android.provider.MediaStore")

        activity = PythonActivity.mActivity
        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        activity.startActivity(intent)


class MainApp(App):
    def build(self):
        self.store = JsonStore("app_state.json")

        if not self.store.exists("welcome"):
            self.root = WelcomeScreen(self)
        else:
            self.root = ArduinoScreen(self)

        return self.root

    def show_arduino_question(self):
        self.root.clear_widgets()
        self.root = ArduinoScreen(self)
        self.root_window.add_widget(self.root)

    # 🔑 Wichtig: nach Kamera zurück zur Arduino-Frage
    def on_resume(self):
        self.root.clear_widgets()
        self.root = ArduinoScreen(self)
        self.root_window.add_widget(self.root)


if __name__ == "__main__":
    MainApp().run()
