import os
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
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle

Window.clearcolor = (0.08, 0.08, 0.1, 1)


class ModernButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = (0.2, 0.2, 0.25, 1)
        self.color = (1, 1, 1, 1)
        self.font_size = 20


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------- SIDEBAR ----------
        sidebar = BoxLayout(
            orientation="vertical",
            size_hint=(0.12, 1),
            spacing=dp(10),
            padding=dp(10)
        )

        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra)
        ]:
            btn = ModernButton(text=text, size_hint=(1, None), height=dp(60))
            btn.bind(on_press=func)
            sidebar.add_widget(btn)

        sidebar.add_widget(Label())
        self.add_widget(sidebar)

        # ---------- CONTENT ----------
        self.content = FloatLayout()
        self.add_widget(self.content)

        self.show_camera()

    # ==================================================
    # CAMERA
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()

        wrapper = FloatLayout()
        self.content.add_widget(wrapper)

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (0.95, None)
        self.camera.height = self.width * 0.5
        self.camera.pos_hint = {"center_x": 0.5, "center_y": 0.5}

        wrapper.add_widget(self.camera)

        # Capture Button
        capture = ModernButton(
            text="●",
            size_hint=(None, None),
            size=(dp(80), dp(80)),
            pos_hint={"right": 0.95, "center_y": 0.5}
        )

        capture.bind(on_press=self.take_photo)
        wrapper.add_widget(capture)

    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)
        self.show_preview(temp_path)

    # ==================================================
    # PREVIEW
    # ==================================================
    def show_preview(self, path):
        self.content.clear_widgets()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path, allow_stretch=True, keep_ratio=True)
        layout.add_widget(img)

        btn_retry = ModernButton(
            text="Wiederholen",
            size_hint=(0.3, 0.1),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = ModernButton(
            text="Speichern",
            size_hint=(0.3, 0.1),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x: self.save_auto(path))
        layout.add_widget(btn_save)

    def save_auto(self, temp_path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        os.rename(temp_path,
                  os.path.join(self.photos_dir, filename))

        self.show_camera()

    # ==================================================
    # GALLERY
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(
            cols=3,
            spacing=dp(15),
            padding=dp(15),
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

            img_btn = Button(
                size_hint_y=None,
                height=dp(180),
                background_normal=path,
                background_down=path
            )
            img_btn.bind(on_press=lambda inst, p=path:
                         self.show_gallery_preview(p))

            grid.add_widget(img_btn)

    def show_gallery_preview(self, path):
        self.content.clear_widgets()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        number = os.path.basename(path).replace(".png", "")

        label = Label(
            text=number,
            size_hint=(None, None),
            size=(dp(120), dp(40)),
            pos_hint={"x": 0.05, "y": 0.02}
        )
        layout.add_widget(label)

    # ==================================================
    # HELP
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(
            text="Hilfe",
            font_size=40,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # EXTRA
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
