import os
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # -------- Sidebar --------
        self.sidebar = BoxLayout(orientation="vertical",
                                 size_hint=(0.2, 1))
        self.add_widget(self.sidebar)

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

        # -------- Rechte Fläche --------
        self.content = FloatLayout()
        self.add_widget(self.content)

        # Ordner für Fotos
        self.photos_dir = os.path.join(App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.show_camera()

    # ==================================================
    # Kamera
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        self.camera = Camera(play=True)
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        # Auslöser
        with self.content.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(
                size=(120, 120),
                pos=(Window.width*0.8 - 150, Window.height/2 - 60)
            )

        self.content.bind(on_touch_down=self.take_photo)

    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size

        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = os.path.join(
                self.photos_dir,
                f"photo_{int(time.time())}.png"
            )
            self.camera.export_to_png(filename)
            self.show_preview(filename)

    # ==================================================
    # Hilfe
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        label = Label(
            text="Hilfe",
            font_size=50,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.content.add_widget(label)

    # ==================================================
    # Galerie
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.content.canvas.clear()

        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=3, spacing=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

        files = sorted(os.listdir(self.photos_dir), reverse=True)

        for file in files:
            if file.endswith(".png"):
                path = os.path.join(self.photos_dir, file)

                btn = Button(size_hint_y=None,
                             height=150,
                             background_normal=path,
                             background_down=path)

                btn.bind(on_press=lambda inst, p=path:
                         self.show_preview(p))

                grid.add_widget(btn)

    # ==================================================
    # Vorschau
    # ==================================================
    def show_preview(self, path):
        self.content.clear_widgets()
        self.content.canvas.clear()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    size_hint=(1, 1),
                    allow_stretch=True)
        layout.add_widget(img)

        # Wiederholen
        btn_retry = Button(text="Wiederholen",
                           size_hint=(0.3, 0.15),
                           pos_hint={"x": 0.1, "y": 0.05})
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        # Fertig
        btn_done = Button(text="Fertig",
                          size_hint=(0.3, 0.15),
                          pos_hint={"x": 0.6, "y": 0.05})
        btn_done.bind(on_press=lambda x: self.save_popup(path))
        layout.add_widget(btn_done)

    # ==================================================
    # Speichern
    # ==================================================
    def save_popup(self, photo_path):

        content = FloatLayout()

        textinput = TextInput(
            hint_text="Dateiname eingeben",
            size_hint=(0.8, 0.2),
            pos_hint={"x": 0.1, "y": 0.5}
        )

        btn_save = Button(
            text="Speichern",
            size_hint=(0.5, 0.2),
            pos_hint={"x": 0.25, "y": 0.2}
        )

        content.add_widget(textinput)
        content.add_widget(btn_save)

        popup = Popup(
            title="Speichern",
            content=content,
            size_hint=(0.8, 0.5)
        )

        def save_file(instance):
            name = textinput.text.strip()
            if name:
                save_path = os.path.join(
                    App.get_running_app().user_data_dir,
                    f"{name}.png"
                )
                with open(photo_path, "rb") as f_src:
                    with open(save_path, "wb") as f_dst:
                        f_dst.write(f_src.read())
                popup.dismiss()

        btn_save.bind(on_press=save_file)
        popup.open()


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
