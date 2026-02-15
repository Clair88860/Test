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

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ---------- TOP BAR ----------
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

        # ---------- CONTENT ----------
        self.content = FloatLayout()
        self.add_widget(self.content)

        # ---------- BOTTOM ----------
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)

        self.create_capture_button()

        Window.bind(on_resize=self.update_orientation)

        self.show_camera()

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

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

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

        btn_retry = Button(
            text="Wiederholen",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.1, "y": 0.05}
        )
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        btn_save = Button(
            text="Speichern",
            size_hint=(0.3, 0.12),
            pos_hint={"x": 0.6, "y": 0.05}
        )
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

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([
            f for f in os.listdir(self.photos_dir)
            if f.endswith(".png")
        ])

        for file in files:
            img_path = os.path.join(self.photos_dir, file)

            btn = Button(
                background_normal=img_path,
                background_down=img_path,
                size_hint_y=None,
                height=250
            )
            btn.bind(on_press=lambda x, f=file: self.open_image_view(f))
            grid.add_widget(btn)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ================= EINZELANSICHT =================
    def open_image_view(self, filename):
        self.content.clear_widgets()

        layout = FloatLayout()
        self.content.add_widget(layout)

        path = os.path.join(self.photos_dir, filename)

        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        name_label = Label(
            text=filename.replace(".png", ""),
            size_hint=(0.6, 0.1),
            pos_hint={"x": 0.05, "y": 0}
        )
        layout.add_widget(name_label)

        info_btn = Button(
            text="i",
            size_hint=(0.1, 0.1),
            pos_hint={"right": 0.95, "y": 0}
        )
        info_btn.bind(on_press=lambda x: self.show_info_popup(filename))
        layout.add_widget(info_btn)

    # ================= INFO POPUP =================
    def show_info_popup(self, filename):

        path = os.path.join(self.photos_dir, filename)
        timestamp = os.path.getmtime(path)
        date_str = datetime.datetime.fromtimestamp(
            timestamp).strftime("%d.%m.%Y %H:%M")

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        name_input = TextInput(
            text=filename.replace(".png", ""),
            multiline=False
        )
        layout.add_widget(name_input)

        layout.add_widget(Label(text=date_str))

        delete_btn = Button(text="Foto löschen")
        layout.add_widget(delete_btn)

        popup = Popup(title="Info", content=layout,
                      size_hint=(0.8, 0.6))

        delete_btn.bind(
            on_press=lambda x: self.confirm_delete(filename, popup)
        )

        name_input.bind(
            on_text_validate=lambda x: self.rename_file(
                filename, name_input.text, popup)
        )

        popup.open()

    def rename_file(self, old_name, new_name, popup):
        old_path = os.path.join(self.photos_dir, old_name)
        new_filename = new_name + ".png"
        new_path = os.path.join(self.photos_dir, new_filename)

        if not os.path.exists(new_path):
            os.rename(old_path, new_path)

        popup.dismiss()
        self.show_gallery()

    def confirm_delete(self, filename, parent_popup):

        layout = BoxLayout(orientation="vertical")

        layout.add_widget(Label(text="Wirklich löschen?"))

        buttons = BoxLayout(size_hint=(1, 0.4))

        btn_yes = Button(text="Ja")
        btn_no = Button(text="Nein")

        buttons.add_widget(btn_yes)
        buttons.add_widget(btn_no)

        layout.add_widget(buttons)

        popup = Popup(title="Sicherheitsfrage",
                      content=layout,
                      size_hint=(0.7, 0.4))

        btn_yes.bind(on_press=lambda x: self.delete_file(
            filename, popup, parent_popup))
        btn_no.bind(on_press=popup.dismiss)

        popup.open()

    def delete_file(self, filename, popup, parent_popup):
        path = os.path.join(self.photos_dir, filename)
        if os.path.exists(path):
            os.remove(path)

        popup.dismiss()
        parent_popup.dismiss()
        self.show_gallery()

    # ================= EXTRA =================
    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0

        layout = GridLayout(cols=3, spacing=10, padding=20)

        layout.add_widget(Label(text="Daten von Arduino"))
        ja1 = Button(text="Ja")
        nein1 = Button(text="Nein")
        ja1.bind(on_press=lambda x: self.toggle(ja1, nein1))
        nein1.bind(on_press=lambda x: self.toggle(nein1, ja1))
        layout.add_widget(ja1)
        layout.add_widget(nein1)

        layout.add_widget(Label(text="Mit Winkel"))
        ja2 = Button(text="Ja")
        nein2 = Button(text="Nein")
        ja2.bind(on_press=lambda x: self.toggle(ja2, nein2))
        nein2.bind(on_press=lambda x: self.toggle(nein2, ja2))
        layout.add_widget(ja2)
        layout.add_widget(nein2)

        self.content.add_widget(layout)

    def toggle(self, active, inactive):
        active.background_color = (0, 1, 0, 1)
        inactive.background_color = (1, 1, 1, 1)

    # ================= HELP =================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 0
        self.content.add_widget(Label(text="Hilfe",
                                      font_size=40,
                                      pos_hint={"center_x": 2.5,
                                                "center_y": 2.5}))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
