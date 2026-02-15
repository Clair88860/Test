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
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Ellipse, Rectangle

try:
    from android.permissions import check_permission, Permission
except ImportError:
    check_permission = None
    Permission = None

Window.clearcolor = (0.08, 0.08, 0.1, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")
        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.camera = None
        self.rotation = None

        # Top Bar
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

        # Content
        self.content = FloatLayout()
        self.add_widget(self.content)

        # Bottom
        self.bottom = FloatLayout(size_hint=(1, 0.15))
        self.add_widget(self.bottom)

        if check_permission and check_permission(Permission.CAMERA):
            self.show_camera()
        else:
            self.show_help()

    # =====================================================
    # ================= CAMERA 16:9 =======================
    # =====================================================

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.clear_widgets()
        self.bottom.opacity = 1

        if not (check_permission and check_permission(Permission.CAMERA)):
            self.bottom.opacity = 0
            self.content.add_widget(Label(
                text="Berechtigung fehlt",
                font_size=40,
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            ))
            return

        # 16:9 Kamera
        self.camera = Camera(
            play=True,
            resolution=(1280, 720)
        )
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        # Drehung
        with self.camera.canvas.before:
            PushMatrix()
            self.rotation = Rotate(angle=-90,
                                   origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rotation,
                         size=self.update_rotation)

        # Runder Button kleiner & höher
        btn = Button(size_hint=(None, None),
                     size=(dp(55), dp(55)),
                     pos_hint={"center_x": 0.5, "y": 0.18},
                     background_normal="",
                     background_color=(1, 1, 1, 1))

        with btn.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=btn.size,
                                  pos=btn.pos)

        btn.bind(pos=self.update_circle,
                 size=self.update_circle)
        btn.bind(on_press=self.take_photo)

        self.bottom.add_widget(btn)

    def update_rotation(self, *args):
        if self.rotation:
            self.rotation.origin = self.camera.center

    def update_circle(self, instance, *args):
        self.circle.pos = instance.pos
        self.circle.size = instance.size

    # =====================================================
    # ================= FOTO ==============================
    # =====================================================

    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)
        self.show_preview(temp_path)

    def show_preview(self, path):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        # Norden Overlay
        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            label = Label(text="Norden",
                          size_hint=(None, None),
                          size=(140, 45),
                          pos_hint={"right": 0.98, "top": 0.98},
                          color=(1, 1, 1, 1),
                          bold=True)

            with label.canvas.before:
                Color(0, 0, 0, 0.8)
                self.rect = Rectangle(size=label.size,
                                      pos=label.pos)

            label.bind(pos=self.update_rect,
                       size=self.update_rect)
            layout.add_widget(label)

        btn_retry = Button(text="Wiederholen",
                           size_hint=(0.3, 0.1),
                           pos_hint={"x": 0.1, "y": 0.05})
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(text="Speichern",
                          size_hint=(0.3, 0.1),
                          pos_hint={"x": 0.6, "y": 0.05})
        btn_save.bind(on_press=lambda x: self.save_photo(path))
        layout.add_widget(btn_save)

    def update_rect(self, instance, *args):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def save_photo(self, temp_path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        os.rename(temp_path,
                  os.path.join(self.photos_dir, filename))

        self.show_camera()

    # =====================================================
    # ================= GALLERY ===========================
    # =====================================================

    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        scroll = ScrollView()
        grid = GridLayout(cols=3,
                          spacing=8,
                          padding=8,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([f for f in os.listdir(self.photos_dir)
                        if f.endswith(".png")])

        for file in files:
            img_path = os.path.join(self.photos_dir, file)

            btn = Button(size_hint_y=None,
                         height=120,
                         background_normal=img_path,
                         background_down=img_path)

            btn.bind(on_press=lambda x, f=file:
                     self.open_image_view(f))

            grid.add_widget(btn)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =====================================================
    # ================= SETTINGS ==========================
    # =====================================================

    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = BoxLayout(orientation="vertical",
                           spacing=20, padding=30)

        row = BoxLayout(spacing=20)
        row.add_widget(Label(text="Daten von Arduino"))

        ja = Button(text="Ja",
                    size_hint=(None, None),
                    size=(90, 40))
        nein = Button(text="Nein",
                      size_hint=(None, None),
                      size=(90, 40))

        ja.bind(on_press=lambda x:
                self.store.put("arduino", value=True))
        nein.bind(on_press=lambda x:
                  self.store.put("arduino", value=False))

        row.add_widget(ja)
        row.add_widget(nein)
        layout.add_widget(row)

        self.content.add_widget(layout)

    # =====================================================

    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0
        self.content.add_widget(Label(
            text="Hilfe",
            font_size=40,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
