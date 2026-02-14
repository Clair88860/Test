from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.core.window import Window
import os
import time

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None


# ───────────── CAMERA / DASHBOARD SCREEN ─────────────
class DashboardScreen(Screen):
    def on_enter(self):
        self.clear_widgets()

        # Gesamt-Layout: Sidebar links, Inhalt rechts
        main_layout = BoxLayout(orientation='horizontal')
        self.add_widget(main_layout)

        # ───────────── Sidebar (links) ─────────────
        sidebar_width = 0.2
        sidebar = BoxLayout(orientation='vertical', size_hint=(sidebar_width, 1))
        main_layout.add_widget(sidebar)

        # Hilfe Button
        btn_help = Button(text='?', size_hint=(1, 0.1), background_color=(0.8, 0.8, 0.8, 1))
        btn_help.bind(on_press=self.show_help)
        sidebar.add_widget(btn_help)

        # Kamera Button
        btn_camera = Button(text='K', size_hint=(1, 0.1), background_color=(0.8, 0.8, 0.8, 1))
        btn_camera.bind(on_press=self.show_camera)
        sidebar.add_widget(btn_camera)

        # Platzhalter für weitere Buttons
        sidebar.add_widget(Label(size_hint=(1, 0.8)))

        # ───────────── Inhalt rechts ─────────────
        self.content_layout = FloatLayout()
        main_layout.add_widget(self.content_layout)

        # Standard: Kamera anzeigen
        self.show_camera()

    # ───────────── Kamera anzeigen ─────────────
    def show_camera(self, *args):
        self.content_layout.clear_widgets()
        # Kamera Fläche füllen (rechte Fläche)
        self.camera = Camera(play=True)
        width = Window.width * 0.8  # rechte Fläche
        height = Window.height
        self.camera.size = (width, height)
        self.camera.pos = (0, 0)
        self.content_layout.add_widget(self.camera)

        # Weißer Auslöser rechts mittig
        with self.content_layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(size=(120, 120), pos=(width - 150, height/2 - 60))

        self.content_layout.bind(on_touch_down=self.take_photo)

    # ───────────── Hilfe anzeigen ─────────────
    def show_help(self, *args):
        self.content_layout.clear_widgets()
        with self.content_layout.canvas:
            Color(0, 0, 0, 0.9)
            Rectangle(size=(Window.width*0.8, Window.height), pos=(0, 0))
        lbl = Label(text="Hier steht die Hilfe", font_size=30, color=(1, 1, 1, 1),
                    pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.content_layout.add_widget(lbl)

    # ───────────── Foto aufnehmen ─────────────
    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size
        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = os.path.join(App.get_running_app().user_data_dir,
                                    f"photo_{int(time.time())}.png")
            self.camera.export_to_png(filename)
            App.get_running_app().last_photo = filename
            self.manager.current = "preview"


# ───────────── PREVIEW SCREEN ─────────────
class PreviewScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        layout = FloatLayout()
        self.add_widget(layout)

        # Schwarzer Hintergrund
        with layout.canvas:
            Color(0, 0, 0, 1)
            Rectangle(size=Window.size, pos=(0, 0))

        photo_path = App.get_running_app().last_photo
        if photo_path and os.path.exists(photo_path):
            image = Image(source=photo_path, size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
            layout.add_widget(image)

        # Wiederholen Button
        btn_retry = Button(text="Wiederholen", size_hint=(0.3, 0.15),
                           pos_hint={"x": 0.1, "y": 0.05}, background_color=(0.2,0.2,0.2,1))
        btn_retry.bind(on_press=self.go_back)
        layout.add_widget(btn_retry)

        # Fertig Button
        btn_done = Button(text="Fertig", size_hint=(0.3,0.15),
                          pos_hint={"x":0.6,"y":0.05}, background_color=(0.2,0.2,0.2,1))
        btn_done.bind(on_press=self.save_photo)
        layout.add_widget(btn_done)

    def go_back(self, instance):
        self.manager.current = "dashboard"

    def save_photo(self, instance):
        photo_path = App.get_running_app().last_photo
        if not photo_path or not os.path.exists(photo_path):
            return

        # Popup für Dateiname
        content = FloatLayout()
        textinput = TextInput(hint_text="Dateiname eingeben", size_hint=(0.8,0.2), pos_hint={"x":0.1,"y":0.5})
        btn_save = Button(text="Speichern", size_hint=(0.5,0.2), pos_hint={"x":0.25,"y":0.2})
        content.add_widget(textinput)
        content.add_widget(btn_save)
        popup = Popup(title="Foto speichern", content=content, size_hint=(0.8,0.5))

        def save_file(instance_btn):
            filename = textinput.text.strip()
            if filename:
                save_path = os.path.join(os.path.expanduser("~/Documents"), f"{filename}.png")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(photo_path, "rb") as f_src:
                    with open(save_path, "wb") as f_dst:
                        f_dst.write(f_src.read())
                popup.dismiss()
        btn_save.bind(on_press=save_file)
        popup.open()


# ───────────── MAIN APP ─────────────
class MainApp(App):
    last_photo = None

    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(PreviewScreen(name="preview"))
        return self.sm

if __name__ == "__main__":
    MainApp().run()
