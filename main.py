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
from kivy.graphics import Color, Ellipse
from kivy.storage.jsonstore import JsonStore

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # TOP BAR
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

        # CONTENT
        self.content = FloatLayout()
        self.add_widget(self.content)

        # BOTTOM
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()

        # EINMALIG prüfen
        if self.camera_available():
            self.show_camera()
        else:
            self.show_help()

    # ================= SETTINGS =================

    def get_setting(self, key):
        if self.store.exists(key):
            return self.store.get(key)["value"]
        return "Nein"

    def set_setting(self, key, value):
        self.store.put(key, value=value)

    # ================= CAMERA CHECK =================

    def camera_available(self):
        try:
            cam = Camera()
            cam.play = False
            return True
        except:
            return False

    # ================= CAMERA BUTTON =================

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

    # ================= CAMERA =================

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        self.camera = Camera(play=True)
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        Window.bind(on_resize=self.update_orientation)
        self.update_orientation()

    def update_orientation(self, *args):
        if hasattr(self, "camera"):
            if Window.height > Window.width:
                self.camera.rotation = -90
            else:
                self.camera.rotation = 0

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

        btn_retry = Button(text="Wiederholen",
                           size_hint=(0.3, 0.12),
                           pos_hint={"x": 0.1, "y": 0.05})
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(text="Speichern",
                          size_hint=(0.3, 0.12),
                          pos_hint={"x": 0.6, "y": 0.05})
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

        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png")]

        if not files:
            self.content.add_widget(Label(
                text="Noch keine Fotos verfügbar",
                font_size=25,
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            ))
            return

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for file in files:
            img_path = os.path.join(self.photos_dir, file)

            box = FloatLayout(size_hint_y=None, height=250)

            img = Image(source=img_path,
                        allow_stretch=True)
            box.add_widget(img)

            btn = Button(background_color=(0, 0, 0, 0))
            btn.bind(on_press=lambda x,
                     f=file:
                     self.open_image_view(f))
            box.add_widget(btn)

            grid.add_widget(box)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ================= EINZELANSICHT =================

    def open_image_view(self, filename):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = FloatLayout()
        self.content.add_widget(layout)

        img_path = os.path.join(self.photos_dir,
                                filename)

        img = Image(source=img_path,
                    allow_stretch=True)
        layout.add_widget(img)

        name_label = Label(
            text=filename,
            size_hint=(1, 0.1),
            pos_hint={"top": 1},
            font_size=20
        )
        layout.add_widget(name_label)

        info_btn = Button(
            text="i",
            size_hint=(0.12, 0.12),
            pos_hint={"right": 0.98,
                      "top": 0.98}
        )
        info_btn.bind(on_press=lambda x:
                      self.show_image_info(filename))
        layout.add_widget(info_btn)

    # ================= INFO POPUP =================

    def show_image_info(self, filename):
        img_path = os.path.join(self.photos_dir,
                                filename)

        timestamp = os.path.getmtime(img_path)
        dt = datetime.datetime.fromtimestamp(timestamp)
        date_str = dt.strftime("%d.%m.%Y %H:%M")

        layout = BoxLayout(orientation="vertical",
                           spacing=10,
                           padding=10)

        layout.add_widget(Label(
            text=f"Name: {filename}\nDatum: {date_str}"
        ))

        rename_btn = Button(text="Umbenennen")
        delete_btn = Button(text="Foto löschen")

        layout.add_widget(rename_btn)
        layout.add_widget(delete_btn)

        popup = Popup(title="Bildinformationen",
                      content=layout,
                      size_hint=(0.8, 0.6))

        rename_btn.bind(on_press=lambda x:
                        self.rename_image(filename, popup))
        delete_btn.bind(on_press=lambda x:
                        self.confirm_delete(filename, popup))

        popup.open()

    # ================= UMBENENNEN =================

    def rename_image(self, filename, parent_popup):
        img_path = os.path.join(self.photos_dir,
                                filename)

        layout = BoxLayout(orientation="vertical",
                           spacing=10,
                           padding=10)

        input_field = TextInput(text=filename,
                                multiline=False)
        layout.add_widget(input_field)

        save_btn = Button(text="Speichern")
        layout.add_widget(save_btn)

        popup = Popup(title="Umbenennen",
                      content=layout,
                      size_hint=(0.8, 0.4))

        def save_name(instance):
            new_name = input_field.text
            if not new_name.endswith(".png"):
                new_name += ".png"

            new_path = os.path.join(self.photos_dir,
                                    new_name)

            os.rename(img_path, new_path)
            popup.dismiss()
            parent_popup.dismiss()
            self.show_gallery()

        save_btn.bind(on_press=save_name)
        popup.open()

    # ================= LÖSCHEN =================

    def confirm_delete(self, filename, parent_popup):
        layout = BoxLayout(orientation="vertical",
                           spacing=10,
                           padding=10)

        layout.add_widget(Label(
            text="Wirklich löschen?"
        ))

        yes_btn = Button(text="Ja")
        no_btn = Button(text="Nein")

        layout.add_widget(yes_btn)
        layout.add_widget(no_btn)

        popup = Popup(title="Sicherheitsabfrage",
                      content=layout,
                      size_hint=(0.7, 0.4))

        def delete(instance):
            os.remove(os.path.join(self.photos_dir,
                                   filename))
            popup.dismiss()
            parent_popup.dismiss()
            self.show_gallery()

        yes_btn.bind(on_press=delete)
        no_btn.bind(on_press=lambda x:
                    popup.dismiss())

        popup.open()

    # ================= HELP =================

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
