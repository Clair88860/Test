import os
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Ellipse, Color
from kivy.metrics import dp
from kivy.clock import Clock
from PIL import Image as PILImage


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        self.thumb_dir = os.path.join(self.photos_dir, "thumbs")
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.thumb_dir, exist_ok=True)

        self.build_camera()
        self.build_topbar()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.5)

    # =====================================================
    # Kamera
    # =====================================================

    def build_camera(self):
        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (.95, .95)
        self.camera.pos_hint = {"center_x": .5, "center_y": .5}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot,
                         size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(80), dp(80)),
            pos_hint={"center_x": .5, "y": .05},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture.size,
                                  pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle,
                          size=self.update_circle)

        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    # =====================================================
    # Topbar
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08),
                                pos_hint={"top": 1})

        for t, f in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

    # =====================================================
    # Kamera anzeigen
    # =====================================================

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.camera)
        self.add_widget(self.topbar)
        self.add_widget(self.capture)

    # =====================================================
    # Foto aufnehmen
    # =====================================================

    def take_photo(self, instance):
        temp = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp)

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False

        if auto:
            self.save_photo(temp)
        else:
            self.preview(temp)

    def preview(self, path):
        self.clear_widgets()
        img = Image(source=path)
        self.add_widget(img)

        btn1 = Button(text="Wiederholen",
                      size_hint=(.3, .1),
                      pos_hint={"x": .1, "y": .05})
        btn1.bind(on_press=lambda x: self.show_camera())

        btn2 = Button(text="Speichern",
                      size_hint=(.3, .1),
                      pos_hint={"x": .6, "y": .05})
        btn2.bind(on_press=lambda x: self.save_photo(path))

        self.add_widget(btn1)
        self.add_widget(btn2)

    def save_photo(self, path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        new_path = os.path.join(self.photos_dir, filename)
        os.rename(path, new_path)

        # Thumbnail
        img = PILImage.open(new_path)
        img.thumbnail((400, 400))
        img.save(os.path.join(self.thumb_dir, filename))

        self.show_camera()

    # =====================================================
    # Galerie
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=3, spacing=10,
                          padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted(os.listdir(self.thumb_dir))

        for file in files:
            layout = FloatLayout(size_hint_y=None,
                                 height=dp(150))

            img = Image(source=os.path.join(self.thumb_dir, file))
            layout.add_widget(img)

            if self.store.exists("arduino") and self.store.get("arduino")["value"]:
                n = Label(text="Norden",
                          size_hint=(None, None),
                          size=(80, 30),
                          pos_hint={"right": .98, "top": .98})
                layout.add_widget(n)

            info = Button(text="i",
                          size_hint=(None, None),
                          size=(30, 30),
                          pos_hint={"right": .98, "y": .02})
            layout.add_widget(info)

            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)

            grid.add_widget(layout)

        scroll.add_widget(grid)
        self.add_widget(scroll)
        self.add_widget(self.topbar)

    # =====================================================
    # Einzelbild
    # =====================================================

    def open_image(self, filename):
        self.clear_widgets()

        path = os.path.join(self.photos_dir, filename)

        layout = BoxLayout(orientation="vertical")

        img = Image(source=path)
        layout.add_widget(img)

        bottom = BoxLayout(size_hint_y=.15)

        name = Label(text=filename)
        info = Button(text="i")
        info.bind(on_press=lambda x: self.image_info(filename))

        bottom.add_widget(name)
        bottom.add_widget(info)

        layout.add_widget(bottom)

        self.add_widget(layout)
        self.add_widget(self.topbar)

    def image_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        stat = os.stat(path)
        dt = datetime.datetime.fromtimestamp(stat.st_mtime)

        box = BoxLayout(orientation="vertical", spacing=10)

        box.add_widget(Label(text="Bildinformationen"))

        rename = Button(text="Umbenennen")
        delete = Button(text="Löschen")

        box.add_widget(Label(text=str(dt)))
        box.add_widget(rename)
        box.add_widget(delete)

        popup = Popup(title="Info",
                      content=box,
                      size_hint=(.7, .6))
        popup.open()

    # =====================================================
    # Einstellungen
    # =====================================================

    def setting_row(self, text, key):
        row = BoxLayout(size_hint_y=None, height=dp(40))
        row.add_widget(Label(text=text))

        for value in [True, False]:
            btn = Button(text="Ja" if value else "Nein",
                         size_hint=(None, None),
                         size=(dp(70), dp(35)))

            def set_value(instance, v=value):
                self.store.put(key, value=v)
                self.show_settings()

            btn.bind(on_press=set_value)

            if self.store.exists(key) and self.store.get(key)["value"] == value:
                btn.background_color = (0, .5, 0, 1)

            row.add_widget(btn)

        return row

    def show_settings(self, *args):
        self.clear_widgets()

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=15)

        layout.add_widget(Label(text="Einstellungen",
                                font_size=28,
                                size_hint_y=None,
                                height=dp(50)))

        layout.add_widget(self.setting_row("Mit Arduino Daten", "arduino"))
        layout.add_widget(self.setting_row("Mit Winkel", "winkel"))
        layout.add_widget(self.setting_row("Automatisches Speichern", "auto"))

        self.add_widget(layout)
        self.add_widget(self.topbar)

    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(Label(text="Hilfe"))
        self.add_widget(self.topbar)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
