import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Ellipse

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ================= TOP BAR =================
        topbar = BoxLayout(size_hint=(1, 0.1), spacing=10)

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

        # ================= CONTENT =================
        self.content = FloatLayout()
        self.add_widget(self.content)

        # ================= BOTTOM BAR =================
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()

        Window.bind(on_resize=self.update_orientation)

        self.show_camera()

    # ==================================================
    # RUNDER BUTTON
    # ==================================================
    def create_capture_button(self):
        self.capture_button = Button(
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            background_normal="",
            background_color=(0, 0, 0, 0),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        with self.capture_button.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture_button.size,
                                  pos=self.capture_button.pos)

        self.capture_button.bind(pos=self.update_circle,
                                 size=self.update_circle)

        self.capture_button.bind(on_press=self.take_photo)

        self.bottom.add_widget(self.capture_button)

    def update_circle(self, *args):
        self.circle.pos = self.capture_button.pos
        self.circle.size = self.capture_button.size

    # ==================================================
    # CAMERA
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        self.update_orientation()

    def update_orientation(self, *args):
        if hasattr(self, "camera"):
            if Window.height > Window.width:
                self.camera.rotation = -90   # richtig nach rechts
            else:
                self.camera.rotation = 0

    # ==================================================
    # FOTO AUFNEHMEN
    # ==================================================
    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)
        self.show_preview(temp_path)

    # ==================================================
    # PREVIEW
    # ==================================================
    def show_preview(self, path):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        # Wiederholen
        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        # Speichern
        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x: self.save_auto(path))
        layout.add_widget(btn_save)

    # ==================================================
    # AUTOMATISCH SPEICHERN
    # ==================================================
    def save_auto(self, temp_path):

        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        final_path = os.path.join(self.photos_dir, filename)

        os.rename(temp_path, final_path)

        self.show_camera()

    # ==================================================
    # HELP
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        self.content.add_widget(Label(
            text="Hilfe",
            font_size=40,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # GALLERY
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        self.content.add_widget(Label(
            text="Galerie kommt als nächstes",
            font_size=30,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # EXTRA
    # ==================================================
    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        self.content.add_widget(Label(
            text="folgt noch\nArduino\nWinkel",
            font_size=30,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
