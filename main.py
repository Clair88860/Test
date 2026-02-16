import os
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.storage.jsonstore import JsonStore
from kivy.metrics import dp

from PIL import Image as PILImage

try:
    from android.permissions import check_permission, Permission
except ImportError:
    check_permission = None
    Permission = None


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")
        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir, "photos")
        self.thumb_dir = os.path.join(self.photos_dir, "thumbs")

        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.thumb_dir, exist_ok=True)

        self.camera = None

        # Top Menü
        top = BoxLayout(size_hint=(1, 0.1))
        for t, f in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            top.add_widget(b)

        self.add_widget(top)

        self.content = FloatLayout()
        self.add_widget(self.content)

        self.bottom = FloatLayout(size_hint=(1, 0.15))
        self.add_widget(self.bottom)

    # ---------------------------------------
    # Kamera erst nach App Start starten!
    # ---------------------------------------

    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.show_camera(), 0.5)

    # ---------------------------------------

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.clear_widgets()
        self.bottom.opacity = 1

        if not (check_permission and check_permission(Permission.CAMERA)):
            self.content.add_widget(Label(
                text="Keine Kamera Berechtigung",
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        self.camera = Camera(
            resolution=(1280, 720),
            play=True
        )
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        btn = Button(
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={"center_x": .5, "y": .2},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )
        btn.bind(on_press=self.take_photo)
        self.bottom.add_widget(btn)

    # ---------------------------------------

    def take_photo(self, instance):
        temp = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp)
        self.save_photo(temp)

    def save_photo(self, path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        new_path = os.path.join(self.photos_dir, filename)
        os.rename(path, new_path)

        # Thumbnail erzeugen
        thumb_path = os.path.join(self.thumb_dir, filename)
        img = PILImage.open(new_path)
        img.thumbnail((400, 225))  # 16:9 Thumbnail
        img.save(thumb_path)

        self.show_camera()

    # ---------------------------------------

    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        scroll = ScrollView()
        grid = GridLayout(cols=3, spacing=10,
                          padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir)
                        if f.endswith(".png")])

        for file in files:
            thumb_path = os.path.join(self.thumb_dir, file)

            if not os.path.exists(thumb_path):
                continue

            layout = FloatLayout(size_hint_y=None,
                                 height=dp(120))

            btn = Button(background_normal=thumb_path,
                         background_down=thumb_path)
            btn.bind(on_press=lambda x, f=file:
                     self.open_image(f))
            layout.add_widget(btn)

            # Nummer
            num = Label(text=file.replace(".png", ""),
                        size_hint=(None, None),
                        size=(50, 30),
                        pos_hint={"x": .02, "top": .98})
            layout.add_widget(num)

            # Info Button
            info = Button(text="i",
                          size_hint=(None, None),
                          size=(30, 30),
                          pos_hint={"right": .98, "top": .98})
            info.bind(on_press=lambda x, f=file:
                      self.show_info(f))
            layout.add_widget(info)

            grid.add_widget(layout)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ---------------------------------------

    def open_image(self, filename):
        self.content.clear_widgets()

        path = os.path.join(self.photos_dir, filename)

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            north = Label(text="Norden",
                          size_hint=(None, None),
                          size=(120, 40),
                          pos_hint={"right": .98, "top": .98})
            layout.add_widget(north)

    def show_info(self, filename):
        popup = Popup(title="Info",
                      content=Label(text=f"Bild: {filename}"),
                      size_hint=(.6, .4))
        popup.open()

    # ---------------------------------------

    def show_settings(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = BoxLayout(orientation="vertical",
                           padding=20, spacing=20)

        row = BoxLayout(spacing=20)
        row.add_widget(Label(text="Arduino Daten?"))

        ja = Button(text="Ja")
        nein = Button(text="Nein")

        ja.bind(on_press=lambda x:
                self.store.put("arduino", value=True))
        nein.bind(on_press=lambda x:
                  self.store.put("arduino", value=False))

        row.add_widget(ja)
        row.add_widget(nein)
        layout.add_widget(row)

        self.content.add_widget(layout)

    # ---------------------------------------

    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0
        self.content.add_widget(Label(
            text="Hilfe",
            pos_hint={"center_x": .5, "center_y": .5}
        ))


class MainApp(App):
    pass


if __name__ == "__main__":
    MainApp().run()
