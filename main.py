import os
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.storage.jsonstore import JsonStore

# Android Permissions
try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None
    Permission = None


Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):
    """Haupt-Dashboard für Kamera, Galerie, Einstellungen"""

    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------- TOP BAR ----------
        topbar = BoxLayout(size_hint=(1, 0.1))
        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra)
        ]:
            btn = Button(text=text)
            btn.bind(on_press=func)
            topbar.add_widget(btn)
        self.add_widget(topbar)

        # ---------- CONTENT ----------
        self.content = FloatLayout()
        self.add_widget(self.content)

        # ---------- BOTTOM ----------
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()
        Window.bind(on_resize=self.update_orientation)

        # Wenn Berechtigung schon da → Kamera, sonst Hilfe-Seite
        if self.check_camera_permission():
            self.show_camera()
        else:
            self.show_permission_help()

    # ================= CAMERA BUTTON =================
    def create_capture_button(self):
        self.capture_button = Button(
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            background_normal="",
            background_color=(0, 0, 0, 0),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.capture_button.bind(on_press=self.take_photo)
        self.bottom.add_widget(self.capture_button)

    # ================= CAMERA =================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)

        # Kamera 90° drehen
        with self.camera.canvas.before:
            PushMatrix()
            self.rotation = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rotation_origin,
                         size=self.update_rotation_origin)
        self.content.add_widget(self.camera)

    def update_rotation_origin(self, *args):
        if hasattr(self, "rotation"):
            self.rotation.origin = self.camera.center

    # ================= FOTO =================
    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)
        self.show_preview(temp_path)

    def show_preview(self, path):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x: self.save_auto(path))
        layout.add_widget(btn_save)

    def save_auto(self, temp_path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]
        filename = f"{len(files)+1:04d}.png"
        final_path = os.path.join(self.photos_dir, filename)
        os.rename(temp_path, final_path)
        self.show_camera()

    # ================= GALERIE =================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=20, padding=20, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        for file in files:
            path = os.path.join(self.photos_dir, file)
            img = Button(
                background_normal=path,
                size_hint_y=None,
                height=350
            )
            grid.add_widget(img)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ================= HELP / PERMISSION =================
    def show_permission_help(self):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = BoxLayout(orientation="vertical", spacing=20, padding=40)

        layout.add_widget(Label(text="Berechtigungen", font_size=36))

        cam_btn = Button(text="Kamera", size_hint=(0.5, 0.15), pos_hint={"center_x": 0.5})
        cam_btn.bind(on_press=self.request_camera_permission)
        layout.add_widget(cam_btn)

        self.content.add_widget(layout)

    def request_camera_permission(self, instance):
        if request_permissions:
            request_permissions([Permission.CAMERA], self.after_permission)

    def after_permission(self, permissions, results):
        if all(results):
            self.show_camera()

    def check_camera_permission(self):
        # Prüfen, ob Berechtigung schon erteilt (nur Android)
        if request_permissions is None:
            return True  # Desktop → immer ok
        try:
            from android.permissions import check_permission
            return check_permission(Permission.CAMERA)
        except:
            return False

    # ================= EXTRA =================
    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = GridLayout(cols=3, padding=40, spacing=20)

        layout.add_widget(Label(text="Daten von Arduino"))
        ja1 = Button(text="Ja", size_hint=(None,None), size=(100,50))
        nein1 = Button(text="Nein", size_hint=(None,None), size=(100,50))
        layout.add_widget(ja1)
        layout.add_widget(nein1)

        layout.add_widget(Label(text="Mit Winkel"))
        ja2 = Button(text="Ja", size_hint=(None,None), size=(100,50))
        nein2 = Button(text="Nein", size_hint=(None,None), size=(100,50))
        layout.add_widget(ja2)
        layout.add_widget(nein2)

        self.content.add_widget(layout)

    # ================= HELP =================
    def show_help(self, *args):
        self.show_permission_help()


class MainApp(App):
    def build(self):
        return Dashboard(self)


if __name__ == "__main__":
    MainApp().run()
