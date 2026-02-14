import os
import time
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Ellipse
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.config import Config

Config.set('graphics', 'resizable', True)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------- SIDEBAR ----------
        self.sidebar = BoxLayout(
            orientation="vertical",
            size_hint=(0.15, 1)
        )
        self.add_widget(self.sidebar)

        for txt, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra)
        ]:
            btn = Button(text=txt, size_hint=(1, 0.1))
            btn.bind(on_press=func)
            self.sidebar.add_widget(btn)

        self.sidebar.add_widget(Label())

        # ---------- CONTENT ----------
        self.content = FloatLayout()
        self.add_widget(self.content)

        Window.bind(on_resize=self.update_camera_size)

        self.show_camera()

    # ==================================================
    # Kamera
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.content.add_widget(self.camera)

        self.update_camera_size()

        with self.content.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(size=(100, 100))

        self.update_button_position()
        self.content.bind(on_touch_down=self.take_photo)

    def update_camera_size(self, *args):
        if hasattr(self, "camera"):
            width = Window.width * 0.85
            height = width * 9 / 16

            if height > Window.height:
                height = Window.height * 0.95
                width = height * 16 / 9

            self.camera.size = (width, height)
            self.camera.pos = (0, (Window.height - height) / 2)

            self.update_button_position()

    def update_button_position(self):
        if hasattr(self, "capture_circle"):
            w, h = self.camera.size
            self.capture_circle.pos = (
                w - 120,
                Window.height / 2 - 50
            )

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            temp_path = os.path.join(self.photos_dir, "temp.png")
            self.camera.export_to_png(temp_path)
            self.show_preview(temp_path)

    # ==================================================
    # Vorschau
    # ==================================================
    def show_preview(self, path):
        self.content.clear_widgets()
        layout = FloatLayout()
        self.content.add_widget(layout)

        layout.add_widget(Image(source=path,
                                allow_stretch=True))

        Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05},
            on_press=lambda x: self.show_camera()
        )
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.15),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x: self.save_auto(path))
        layout.add_widget(btn_save)

    def save_auto(self, temp_path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        next_number = len(files) + 1
        filename = f"{next_number:04d}.png"

        os.rename(temp_path,
                  os.path.join(self.photos_dir, filename))

        self.show_camera()

    # ==================================================
    # Galerie
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=2,
                          spacing=20,
                          size_hint_y=None)
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

    def show_gallery_preview(self, path):
        self.content.clear_widgets()
        layout = FloatLayout()
        self.content.add_widget(layout)

        layout.add_widget(Image(source=path,
                                allow_stretch=True))

        number = os.path.basename(path).replace(".png", "")

        label = Label(
            text=number,
            size_hint=(0.3, 0.1),
            pos_hint={"x": 0.05, "y": 0}
        )
        layout.add_widget(label)

        btn_info = Button(
            text="i",
            size_hint=(0.1, 0.1),
            pos_hint={"right": 0.95, "y": 0}
        )
        btn_info.bind(on_press=lambda x:
                      self.show_info_popup(path))
        layout.add_widget(btn_info)

    # ==================================================
    # Info Popup
    # ==================================================
    def show_info_popup(self, path):
        content = BoxLayout(orientation="vertical", spacing=10)

        filename = os.path.basename(path)
        number = filename.replace(".png", "")

        # Umbenennen
        txt = TextInput(text=number, multiline=False)
        content.add_widget(txt)

        # Datum
        timestamp = os.path.getmtime(path)
        date_str = datetime.fromtimestamp(timestamp)\
            .strftime("%d.%m.%Y %H:%M:%S")
        content.add_widget(Label(text=date_str))

        # Löschen Button
        btn_delete = Button(text="Foto löschen")
        content.add_widget(btn_delete)

        popup = Popup(title="Info",
                      content=content,
                      size_hint=(0.8, 0.6))

        def rename(instance):
            new_name = txt.text.strip()
            if new_name:
                new_path = os.path.join(
                    self.photos_dir,
                    f"{new_name}.png"
                )
                os.rename(path, new_path)
                popup.dismiss()
                self.show_gallery()

        txt.bind(on_text_validate=rename)

        def confirm_delete(instance):
            confirm = Popup(
                title="Wirklich löschen?",
                content=BoxLayout(),
                size_hint=(0.7, 0.4)
            )
            box = BoxLayout(orientation="vertical")
            box.add_widget(Label(text="Möchten sie das Foto wirklich löschen?"))

            btn_yes = Button(text="Ja")
            btn_no = Button(text="Nein")

            box.add_widget(btn_yes)
            box.add_widget(btn_no)

            confirm.content = box

            btn_yes.bind(on_press=lambda x: (
                os.remove(path),
                confirm.dismiss(),
                popup.dismiss(),
                self.show_gallery()
            ))

            btn_no.bind(on_press=confirm.dismiss)

            confirm.open()

        btn_delete.bind(on_press=confirm_delete)

        popup.open()

    # ==================================================
    # Hilfe
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(
            text="Hilfe",
            font_size=50,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # Extra
    # ==================================================
    def show_extra(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(
            text="folgt noch\nArduino\nWinkel",
            font_size=30,
            halign="center",
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
