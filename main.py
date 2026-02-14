import os
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # ---------- Ordner ----------
        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------- Sidebar ----------
        self.sidebar = BoxLayout(
            orientation="vertical",
            size_hint=(0.15, 1)
        )
        self.add_widget(self.sidebar)

        Button(text="?", size_hint=(1, 0.1),
               on_press=self.show_help).\
            bind(on_press=self.show_help)

        btn_help = Button(text="?", size_hint=(1, 0.1))
        btn_help.bind(on_press=self.show_help)
        self.sidebar.add_widget(btn_help)

        btn_camera = Button(text="K", size_hint=(1, 0.1))
        btn_camera.bind(on_press=self.show_camera)
        self.sidebar.add_widget(btn_camera)

        btn_gallery = Button(text="G", size_hint=(1, 0.1))
        btn_gallery.bind(on_press=self.show_gallery)
        self.sidebar.add_widget(btn_gallery)

        self.sidebar.add_widget(Label())

        # ---------- Content ----------
        self.content = FloatLayout()
        self.add_widget(self.content)

        self.show_camera()

    # ==================================================
    # Kamera 16:9
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        width = Window.width * 0.85
        height = width * 9 / 16

        self.camera = Camera(play=True,
                             resolution=(1280, 720))
        self.camera.size = (width, height)
        self.camera.pos = (0, (Window.height - height) / 2)

        self.content.add_widget(self.camera)

        # Auslöser
        with self.content.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(100, 100),
                pos=(width - 120,
                     Window.height/2 - 50)
            )

        self.content.bind(on_touch_down=self.take_photo)

    # ==================================================
    # Foto aufnehmen
    # ==================================================
    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            temp_path = os.path.join(
                self.photos_dir,
                "temp.png"
            )
            self.camera.export_to_png(temp_path)
            self.show_preview(temp_path)

    # ==================================================
    # Vorschau
    # ==================================================
    def show_preview(self, path):
        self.content.clear_widgets()
        self.content.canvas.clear()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        # Wiederholen
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x:
                       self.show_camera())
        layout.add_widget(btn_retry)

        # Speichern
        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x:
                      self.save_auto(path))
        layout.add_widget(btn_save)

    # ==================================================
    # Automatisch speichern 0001, 0002 ...
    # ==================================================
    def save_auto(self, temp_path):

        existing = sorted([
            f for f in os.listdir(self.photos_dir)
            if f.endswith(".png") and f != "temp.png"
        ])

        next_number = len(existing) + 1
        filename = f"{next_number:04d}.png"

        save_path = os.path.join(
            self.photos_dir,
            filename
        )

        os.rename(temp_path, save_path)

        # Zurück zur Kamera
        self.show_camera()

    # ==================================================
    # Hilfe
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        label = Label(
            text="Hilfe",
            font_size=50,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        )
        self.content.add_widget(label)

    # ==================================================
    # Galerie
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        scroll = ScrollView()
        grid = GridLayout(
            cols=2,
            spacing=20,
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

        files = sorted(
            [f for f in os.listdir(self.photos_dir)
             if f.endswith(".png") and f != "temp.png"]
        )

        for file in files:
            path = os.path.join(self.photos_dir, file)

            btn = Button(
                size_hint_y=None,
                height=250,
                background_normal=path,
                background_down=path
            )

            btn.bind(on_press=lambda inst, p=path:
                     self.show_gallery_preview(p))

            grid.add_widget(btn)

    # ==================================================
    # Galerie-Vorschau
    # ==================================================
    def show_gallery_preview(self, path):
        self.content.clear_widgets()
        self.content.canvas.clear()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        number = os.path.basename(path).replace(".png", "")

        label = Label(
            text=number,
            size_hint=(1, 0.1),
            pos_hint={"center_x": 0.5,
                      "y": 0}
        )
        layout.add_widget(label)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
