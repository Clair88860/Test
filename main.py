import os
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.current_popup = None

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # =====================================================
    # Nummerierung
    # =====================================================

    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    # =====================================================
    # Topbar
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(
            size_hint=(1, .08),
            pos_hint={"top": 1},
            spacing=5,
            padding=5
        )

        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a),
            ("H", self.show_help)
        ]:
            b = Button(
                text=t,
                background_normal="",
                background_color=(0.15, 0.15, 0.15, 1),
                color=(1, 1, 1, 1)
            )
            b.bind(on_press=f)
            self.topbar.add_widget(b)

        self.add_widget(self.topbar)

    # =====================================================
    # Kamera
    # =====================================================

    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920, 1080))
        self.camera.size_hint = (1, .9)
        self.camera.pos_hint = {"center_x": .5, "center_y": .45}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={"center_x": .5, "y": .04},
            background_normal="",
            background_color=(0, 0, 0, 0)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.outer_circle = Ellipse(size=self.capture.size,
                                        pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle,
                          size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size

    def show_camera(self, *args):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # Foto
    # =====================================================

    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)
        self.show_camera()

    # =====================================================
    # Galerie
    # =====================================================

    def show_gallery(self, *args):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        if not files:
            self.add_widget(Label(
                text="Es wurden noch keine Fotos gemacht",
                font_size=24,
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        scroll = ScrollView()
        grid = GridLayout(
            cols=2,
            spacing=10,
            padding=[10, 120, 10, 10],
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(280),
                spacing=5
            )

            img = Image(
                source=os.path.join(self.photos_dir, file),
                allow_stretch=True
            )

            img.bind(on_release=lambda inst, f=file: self.open_image(f))

            name = Label(
                text=file.replace(".png", ""),
                size_hint_y=None,
                height=dp(25)
            )

            box.add_widget(img)
            box.add_widget(name)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # Einzelansicht
    # =====================================================

    def open_image(self, filename):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")

        img_layout = FloatLayout(size_hint_y=0.85)

        path = os.path.join(self.photos_dir, filename)
        img = Image(source=path, allow_stretch=True)
        img_layout.add_widget(img)

        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            overlay = Label(
                text="Norden",
                color=(1, 0, 0, 1),
                font_size=24,
                size_hint=(None, None),
                size=(dp(100), dp(40)),
                pos_hint={"right": 0.98, "top": 0.98}
            )
            img_layout.add_widget(overlay)

        layout.add_widget(img_layout)

        bottom = BoxLayout(orientation="vertical", size_hint_y=0.15)

        name_lbl = Label(text=filename.replace(".png", ""))
        info_btn = Button(text="i", size_hint=(None, None), size=(dp(40), dp(40)))
        info_btn.bind(on_press=lambda x: self.show_info(filename))

        row = BoxLayout()
        row.add_widget(name_lbl)
        row.add_widget(info_btn)

        bottom.add_widget(row)
        layout.add_widget(bottom)
        self.add_widget(layout)

    # =====================================================
    # Info + Löschen
    # =====================================================

    def show_info(self, filename):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.confirm_delete(filename))

        box.add_widget(delete_btn)

        popup = Popup(title=filename, content=box, size_hint=(0.7, 0.4))
        self.current_popup = popup
        popup.open()

    def confirm_delete(self, filename):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="Wirklich löschen?"))

        yes = Button(text="Ja")
        no = Button(text="Nein")

        yes.bind(on_press=lambda x: self.delete_file(filename))
        no.bind(on_press=lambda x: self.close_popup())

        box.add_widget(yes)
        box.add_widget(no)

        popup = Popup(title="Sicher?", content=box, size_hint=(0.7, 0.4))
        self.current_popup = popup
        popup.open()

    def delete_file(self, filename):
        path = os.path.join(self.photos_dir, filename)
        if os.path.exists(path):
            os.remove(path)

        self.close_popup()
        self.show_gallery()

    def close_popup(self):
        if self.current_popup:
            self.current_popup.dismiss()
            self.current_popup = None

    # =====================================================
    # Weitere Seiten
    # =====================================================

    def show_settings(self, *args):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Einstellungen",
                              pos_hint={"center_x": .5, "center_y": .5}))

    def show_a(self, *args):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="A Seite",
                              pos_hint={"center_x": .5, "center_y": .5}))

    def show_help(self, *args):
        self.close_popup()
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe Seite",
                              pos_hint={"center_x": .5, "center_y": .5}))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
