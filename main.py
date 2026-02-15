import os
import datetime
from PIL import Image as PILImage, ImageDraw, ImageFont

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
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse

try:
    from android.permissions import check_permission, Permission
except ImportError:
    check_permission = None
    Permission = None

Window.clearcolor = (0.08, 0.08, 0.1, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.store = JsonStore("settings.json")

        base_dir = App.get_running_app().user_data_dir
        self.photos_dir = os.path.join(base_dir, "photos")
        self.thumb_dir = os.path.join(self.photos_dir, "thumbs")

        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.thumb_dir, exist_ok=True)

        self.camera = None

        # Top Bar
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

        self.content = FloatLayout()
        self.add_widget(self.content)

        self.bottom = FloatLayout(size_hint=(1, 0.15))
        self.add_widget(self.bottom)

        if check_permission and check_permission(Permission.CAMERA):
            self.show_camera()
        else:
            self.show_help()

    # =====================================================
    # ================= CAMERA ============================
    # =====================================================

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.clear_widgets()
        self.bottom.opacity = 1

        if not (check_permission and check_permission(Permission.CAMERA)):
            self.bottom.opacity = 0
            self.content.add_widget(Label(
                text="Berechtigung fehlt",
                font_size=40,
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            ))
            return

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        btn = Button(size_hint=(None, None),
                     size=(dp(55), dp(55)),
                     pos_hint={"center_x": 0.5, "y": 0.18},
                     background_normal="",
                     background_color=(1, 1, 1, 1))

        with btn.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=btn.size, pos=btn.pos)

        btn.bind(pos=self.update_circle,
                 size=self.update_circle)
        btn.bind(on_press=self.take_photo)

        self.bottom.add_widget(btn)

    def update_circle(self, instance, *args):
        self.circle.pos = instance.pos
        self.circle.size = instance.size

    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)
        self.save_photo(temp_path)

    # =====================================================
    # ================= SPEICHERN =========================
    # =====================================================

    def save_photo(self, temp_path):

        files = [f for f in os.listdir(self.photos_dir)
                 if f.endswith(".png") and f != "temp.png"]

        filename = f"{len(files)+1:04d}.png"
        final_path = os.path.join(self.photos_dir, filename)
        os.rename(temp_path, final_path)

        # Norden ins Original einzeichnen
        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            img = PILImage.open(final_path)
            draw = ImageDraw.Draw(img)

            font_size = int(img.width / 18)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = None

            text = "Norden"
            text_width = font_size * 4
            text_height = font_size + 10

            x = img.width - text_width - 20
            y = 20

            draw.rectangle(
                [x - 10, y - 5, x + text_width, y + text_height],
                fill=(0, 0, 0, 200)
            )
            draw.text((x, y),
                      text,
                      fill=(255, 255, 255),
                      font=font)

            img.save(final_path)

        # Thumbnail erstellen
        thumb_path = os.path.join(self.thumb_dir, filename)
        img = PILImage.open(final_path)
        img.thumbnail((400, 400))
        img.save(thumb_path)

        self.show_camera()

    # =====================================================
    # ================= GALLERY ===========================
    # =====================================================

    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        scroll = ScrollView()
        grid = GridLayout(cols=3,
                          spacing=8,
                          padding=8,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([f for f in os.listdir(self.photos_dir)
                        if f.endswith(".png")])

        for file in files:
            thumb_path = os.path.join(self.thumb_dir, file)

            container = FloatLayout(size_hint_y=None,
                                    height=120)

            btn = Button(background_normal=thumb_path,
                         background_down=thumb_path,
                         size_hint=(1, 1))

            btn.bind(on_press=lambda x, f=file:
                     self.open_image_view(f))

            container.add_widget(btn)

            # Zahl unten links
            label = Label(text=file.replace(".png", ""),
                          size_hint=(None, None),
                          size=(80, 30),
                          pos_hint={"x": 0.02, "y": 0.02})
            container.add_widget(label)

            # Info Button unten rechts
            info_btn = Button(text="i",
                              size_hint=(None, None),
                              size=(30, 30),
                              pos_hint={"right": 0.98, "y": 0.02})

            info_btn.bind(on_press=lambda x, f=file:
                          self.show_info_popup(f))

            container.add_widget(info_btn)

            grid.add_widget(container)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =====================================================
    # ================= FOTO ANSICHT ======================
    # =====================================================

    def open_image_view(self, filename):
        self.content.clear_widgets()

        layout = FloatLayout()
        self.content.add_widget(layout)

        path = os.path.join(self.photos_dir, filename)

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        layout.add_widget(img)

    # =====================================================
    # ================= INFO POPUP ========================
    # =====================================================

    def show_info_popup(self, filename):
        path = os.path.join(self.photos_dir, filename)

        timestamp = os.path.getmtime(path)
        date_str = datetime.datetime.fromtimestamp(
            timestamp).strftime("%d.%m.%Y %H:%M")

        layout = BoxLayout(orientation="vertical",
                           spacing=10,
                           padding=10)

        name_input = TextInput(
            text=filename.replace(".png", ""),
            multiline=False)

        layout.add_widget(name_input)
        layout.add_widget(Label(text=date_str))

        delete_btn = Button(text="Foto löschen")
        layout.add_widget(delete_btn)

        popup = Popup(title="Info",
                      content=layout,
                      size_hint=(0.8, 0.6))

        delete_btn.bind(
            on_press=lambda x:
            self.delete_photo(filename, popup)
        )

        name_input.bind(
            on_text_validate=lambda x:
            self.rename_photo(filename,
                              name_input.text,
                              popup)
        )

        popup.open()

    def rename_photo(self, old_name, new_name, popup):
        old_path = os.path.join(self.photos_dir, old_name)
        new_name_full = new_name + ".png"
        new_path = os.path.join(self.photos_dir, new_name_full)

        os.rename(old_path, new_path)

        # Thumbnail auch umbenennen
        old_thumb = os.path.join(self.thumb_dir, old_name)
        new_thumb = os.path.join(self.thumb_dir, new_name_full)
        if os.path.exists(old_thumb):
            os.rename(old_thumb, new_thumb)

        popup.dismiss()
        self.show_gallery()

    def delete_photo(self, filename, popup):
        os.remove(os.path.join(self.photos_dir, filename))

        thumb = os.path.join(self.thumb_dir, filename)
        if os.path.exists(thumb):
            os.remove(thumb)

        popup.dismiss()
        self.show_gallery()

    # =====================================================

    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = BoxLayout(orientation="vertical",
                           spacing=20,
                           padding=30)

        row = BoxLayout(spacing=20)
        row.add_widget(Label(text="Daten von Arduino"))

        ja = Button(text="Ja",
                    size_hint=(None, None),
                    size=(90, 40))
        nein = Button(text="Nein",
                      size_hint=(None, None),
                      size=(90, 40))

        ja.bind(on_press=lambda x:
                self.store.put("arduino", value=True))
        nein.bind(on_press=lambda x:
                  self.store.put("arduino", value=False))

        row.add_widget(ja)
        row.add_widget(nein)
        layout.add_widget(row)

        self.content.add_widget(layout)

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
