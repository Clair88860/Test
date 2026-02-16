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
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.metrics import dp

from PIL import Image as PILImage
from PIL import ImageDraw
from PIL import ImageFont

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        self.thumb_dir = os.path.join(self.photos_dir, "thumbs")

        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.thumb_dir, exist_ok=True)

        # Kamera Hintergrund (fullscreen)
        self.camera = Camera(resolution=(1280, 720), play=True)
        self.camera.size_hint = (1, 1)
        self.add_widget(self.camera)

        # Top Menü (liegt drüber)
        self.topbar = BoxLayout(size_hint=(1, 0.1),
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

        self.add_widget(self.topbar)

        # Kamera Button (liegt drüber)
        self.capture_btn = Button(
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={"center_x": .5, "y": .05},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )
        self.capture_btn.bind(on_press=self.take_photo)
        self.add_widget(self.capture_btn)

        Clock.schedule_once(lambda dt: self.show_camera(), 0.5)

    # =====================================================
    # Kamera
    # =====================================================

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.camera)
        self.add_widget(self.topbar)
        self.add_widget(self.capture_btn)

    def take_photo(self, instance):
        temp = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp)

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False

        if auto:
            self.save_photo(temp)
        else:
            self.preview(temp)

    # =====================================================
    # Vorschau
    # =====================================================

    def preview(self, path):
        self.clear_widgets()

        img = Image(source=path, allow_stretch=True, keep_ratio=True)
        self.add_widget(img)

        btn1 = Button(text="Wiederholen",
                      size_hint=(.3, .1),
                      pos_hint={"x": .1, "y": .05})
        btn1.bind(on_press=lambda x: self.show_camera())
        self.add_widget(btn1)

        btn2 = Button(text="Speichern",
                      size_hint=(.3, .1),
                      pos_hint={"x": .6, "y": .05})
        btn2.bind(on_press=lambda x: self.save_photo(path))
        self.add_widget(btn2)

    # =====================================================
    # Speichern + Norden ins Bild einbrennen
    # =====================================================

    def save_photo(self, path):
        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        new_path = os.path.join(self.photos_dir, filename)
        os.rename(path, new_path)

        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            img = PILImage.open(new_path)
            draw = ImageDraw.Draw(img)
            draw.text((img.width - 200, 30), "Norden", fill=(255, 0, 0))
            img.save(new_path)

        thumb = os.path.join(self.thumb_dir, filename)
        img = PILImage.open(new_path)
        img.thumbnail((400, 225))
        img.save(thumb)

        self.show_camera()

    # =====================================================
    # Galerie
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=3,
                          spacing=10,
                          padding=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir)
                        if f.endswith(".png")])

        for file in files:
            layout = BoxLayout(orientation="vertical",
                               size_hint_y=None,
                               height=dp(160))

            img = Image(source=os.path.join(self.thumb_dir, file),
                        size_hint_y=.8)
            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)

            info_row = BoxLayout(size_hint_y=.2)

            number = Label(text=file.replace(".png", ""))
            info_btn = Button(text="i")
            info_btn.bind(on_press=lambda x, f=file:
                          self.show_info(f))

            info_row.add_widget(number)
            info_row.add_widget(info_btn)

            layout.add_widget(img)
            layout.add_widget(info_row)

            grid.add_widget(layout)

        scroll.add_widget(grid)
        self.add_widget(scroll)
        self.add_widget(self.topbar)

    # =====================================================
    # Einzelansicht
    # =====================================================

    def open_image(self, filename):
        self.clear_widgets()

        path = os.path.join(self.photos_dir, filename)

        layout = BoxLayout(orientation="vertical")

        img = Image(source=path, allow_stretch=True, keep_ratio=True)
        layout.add_widget(img)

        info = BoxLayout(size_hint_y=.2)

        stat = os.stat(path)
        dt = datetime.datetime.fromtimestamp(stat.st_mtime)

        name_label = Label(text=f"{filename}\n{dt}")

        rename = Button(text="Umbenennen")
        rename.bind(on_press=lambda x:
                    self.rename_popup(filename))

        delete = Button(text="Löschen")
        delete.bind(on_press=lambda x:
                    self.delete_popup(filename))

        info.add_widget(name_label)
        info.add_widget(rename)
        info.add_widget(delete)

        layout.add_widget(info)

        self.add_widget(layout)
        self.add_widget(self.topbar)

    # =====================================================
    # Umbenennen
    # =====================================================

    def rename_popup(self, filename):
        box = BoxLayout(orientation="vertical")
        txt = TextInput(text=filename.replace(".png", ""))
        btn = Button(text="Speichern")

        def rename_file(instance):
            new_name = txt.text + ".png"
            os.rename(
                os.path.join(self.photos_dir, filename),
                os.path.join(self.photos_dir, new_name)
            )
            popup.dismiss()
            self.show_gallery()

        btn.bind(on_press=rename_file)
        box.add_widget(txt)
        box.add_widget(btn)

        popup = Popup(title="Umbenennen",
                      content=box,
                      size_hint=(.7, .5))
        popup.open()

    # =====================================================
    # Löschen
    # =====================================================

    def delete_popup(self, filename):
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(text="Wirklich löschen?"))

        btn_yes = Button(text="Ja")
        btn_no = Button(text="Nein")

        def delete_file(instance):
            os.remove(os.path.join(self.photos_dir, filename))
            popup.dismiss()
            self.show_gallery()

        btn_yes.bind(on_press=delete_file)
        btn_no.bind(on_press=lambda x: popup.dismiss())

        box.add_widget(btn_yes)
        box.add_widget(btn_no)

        popup = Popup(title="Löschen",
                      content=box,
                      size_hint=(.6, .4))
        popup.open()

    # =====================================================
    # Einstellungen
    # =====================================================

    def show_settings(self, *args):
        self.clear_widgets()

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=20)

        layout.add_widget(Label(text="Automatisch speichern?"))

        row = BoxLayout(spacing=20)

        yes = Button(text="Ja",
                     background_color=(0, 1, 0, 1))
        no = Button(text="Nein",
                    background_color=(1, 0, 0, 1))

        yes.bind(on_press=lambda x:
                 self.store.put("auto", value=True))
        no.bind(on_press=lambda x:
                self.store.put("auto", value=False))

        row.add_widget(yes)
        row.add_widget(no)

        layout.add_widget(row)

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
