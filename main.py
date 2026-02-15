import os
import shutil
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.core.window import Window

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")
        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir, "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------------- TOP BAR ----------------
        top = BoxLayout(size_hint=(1, 0.1))
        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings)
        ]:
            b = Button(text=text)
            b.bind(on_press=func)
            top.add_widget(b)
        self.add_widget(top)

        # ---------------- CONTENT ----------------
        self.content = FloatLayout()
        self.add_widget(self.content)

        # ---------------- BOTTOM ----------------
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()

        # START
        self.start_screen()

    # =====================================================
    # START LOGIK
    # =====================================================
    def start_screen(self):
        if self.camera_available():
            self.show_camera()
        else:
            self.show_help()

    def camera_available(self):
        try:
            cam = Camera()
            cam.play = False
            return True
        except:
            return False

    # =====================================================
    # RUNDER BUTTON
    # =====================================================
    def create_capture_button(self):
        self.capture_btn = Button(
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            background_normal="",
            background_color=(0, 0, 0, 0),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        with self.capture_btn.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(
                size=self.capture_btn.size,
                pos=self.capture_btn.pos
            )

        self.capture_btn.bind(pos=self.update_circle,
                              size=self.update_circle)
        self.capture_btn.bind(on_press=self.take_photo)
        self.bottom.add_widget(self.capture_btn)

    def update_circle(self, *args):
        self.circle.pos = self.capture_btn.pos
        self.circle.size = self.capture_btn.size

    # =====================================================
    # CAMERA
    # =====================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        if not self.camera_available():
            self.content.add_widget(Label(
                text="Keine Berechtigung verfügbar",
                font_size=25,
                pos_hint={"center_x": 0.5,
                          "center_y": 0.5}
            ))
            self.bottom.opacity = 0
            return

        self.camera = Camera(
            play=True,
            resolution=(1280, 960)  # 4:3 Format
        )
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

    # =====================================================
    # FOTO
    # =====================================================
    def take_photo(self, *args):
        temp = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp)
        self.show_preview(temp)

    def show_preview(self, path):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        if self.is_arduino_on():
            self.draw_red_dot(layout)

        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.1),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.1),
            pos_hint={"x": 0.6, "y": 0.05}
        )
        btn_save.bind(on_press=lambda x: self.save_photo(path))
        layout.add_widget(btn_save)

    def save_photo(self, temp):
        number = self.get_next_number()
        filename = f"{number:04d}.png"
        final = os.path.join(self.photos_dir, filename)

        shutil.move(temp, final)

        self.store.put(filename,
                       name=f"{number:04d}",
                       date=str(datetime.now()))

        self.show_camera()

    def get_next_number(self):
        files = [
            f for f in os.listdir(self.photos_dir)
            if f.endswith(".png")
        ]
        numbers = [
            int(f.replace(".png", ""))
            for f in files if f.replace(".png", "").isdigit()
        ]
        return max(numbers) + 1 if numbers else 1

    # =====================================================
    # GALERIE
    # =====================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        files = sorted(
            [f for f in os.listdir(self.photos_dir)
             if f.endswith(".png")],
            reverse=True
        )

        if not files:
            self.content.add_widget(Label(
                text="Noch keine Fotos verfügbar",
                font_size=22,
                pos_hint={"center_x": 0.5,
                          "center_y": 0.5}
            ))
            return

        scroll = ScrollView()
        grid = GridLayout(cols=2,
                          spacing=10,
                          padding=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            path = os.path.join(self.photos_dir, file)

            box = FloatLayout(size_hint_y=None,
                              height=dp(200))

            img = Image(source=path,
                        allow_stretch=True,
                        keep_ratio=True)
            box.add_widget(img)

            if self.is_arduino_on():
                self.draw_red_dot(box)

            btn = Button(background_color=(0, 0, 0, 0))
            btn.bind(on_press=lambda x,
                     p=path: self.open_image(p))
            box.add_widget(btn)

            grid.add_widget(box)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =====================================================
    # EINZELBILD
    # =====================================================
    def open_image(self, path):
        self.content.clear_widgets()

        layout = FloatLayout()
        self.content.add_widget(layout)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

        if self.is_arduino_on():
            self.draw_red_dot(layout)

        filename = os.path.basename(path)
        name = self.store.get(filename)["name"] \
            if self.store.exists(filename) else filename

        label = Label(text=name,
                      size_hint=(0.6, 0.1),
                      pos_hint={"x": 0.05, "y": 0.02})
        layout.add_widget(label)

        info = Button(text="i",
                      size_hint=(0.15, 0.1),
                      pos_hint={"right": 0.95,
                                "y": 0.02})
        info.bind(on_press=lambda x:
                  self.show_info(path))
        layout.add_widget(info)

    # =====================================================
    # INFO POPUP
    # =====================================================
    def show_info(self, path):
        filename = os.path.basename(path)

        data = self.store.get(filename) \
            if self.store.exists(filename) else {}

        box = BoxLayout(orientation="vertical",
                        spacing=10,
                        padding=10)

        txt = TextInput(text=data.get("name", filename))
        box.add_widget(txt)

        box.add_widget(Label(
            text="Datum:\n" + data.get("date", "")
        ))

        save = Button(text="Umbenennen")
        save.bind(on_press=lambda x:
                  self.rename_photo(path, txt.text))
        box.add_widget(save)

        delete = Button(text="Foto löschen")
        delete.bind(on_press=lambda x:
                    self.confirm_delete(path))
        box.add_widget(delete)

        Popup(title="Info",
              content=box,
              size_hint=(0.8, 0.7)).open()

    def rename_photo(self, path, new_name):
        filename = os.path.basename(path)
        if self.store.exists(filename):
            data = self.store.get(filename)
            self.store.put(filename,
                           name=new_name,
                           date=data["date"])

    def confirm_delete(self, path):
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(
            text="Wirklich löschen?"
        ))

        yes = Button(text="Ja")
        yes.bind(on_press=lambda x:
                 self.delete_photo(path))

        box.add_widget(yes)

        Popup(title="Sicher?",
              content=box,
              size_hint=(0.6, 0.4)).open()

    def delete_photo(self, path):
        os.remove(path)
        self.show_gallery()

    # =====================================================
    # SETTINGS
    # =====================================================
    def show_settings(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = BoxLayout(orientation="vertical",
                           spacing=20,
                           padding=20)

        layout.add_widget(Label(
            text="Einstellung",
            font_size=28,
            size_hint=(1, 0.2)
        ))

        layout.add_widget(
            self.settings_row(
                "Daten von Arduino",
                "arduino"
            )
        )

        layout.add_widget(
            self.settings_row(
                "Mit Winkel",
                "winkel"
            )
        )

        self.content.add_widget(layout)

    def settings_row(self, text, key):
        row = BoxLayout()

        row.add_widget(Label(text=text))

        current = self.store.get(key)["value"] \
            if self.store.exists(key) else "Nein"

        for val in ["Ja", "Nein"]:
            color = (0, 0.5, 0, 1) \
                if val == current else (1, 1, 1, 1)

            btn = Button(text=val,
                         background_color=color)
            btn.bind(on_press=lambda x,
                     v=val: self.set_setting(key, v))
            row.add_widget(btn)

        return row

    def set_setting(self, key, value):
        self.store.put(key, value=value)
        self.show_settings()

    def is_arduino_on(self):
        return self.store.exists("arduino") and \
               self.store.get("arduino")["value"] == "Ja"

    # =====================================================
    # RED DOT
    # =====================================================
    def draw_red_dot(self, parent):
        with parent.canvas:
            Color(1, 0, 0, 1)
            Ellipse(size=(dp(20), dp(20)),
                    pos=(dp(10),
                         parent.height - dp(30)))

    # =====================================================
    # HELP
    # =====================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        self.content.add_widget(Label(
            text="Hilfe\n\nK = Kamera\nG = Galerie\nE = Einstellungen",
            font_size=24,
            halign="center",
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
