import os
import shutil
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.storage.jsonstore import JsonStore


class CameraApp(App):

    def build(self):

        self.store = JsonStore("settings.json")
        self.photos_dir = "photos"

        if not os.path.exists(self.photos_dir):
            os.makedirs(self.photos_dir)

        self.root = BoxLayout(orientation="vertical")

        # =======================
        # TOP NAVIGATION
        # =======================
        nav = BoxLayout(size_hint_y=0.1)

        nav.add_widget(Button(text="?", on_press=self.show_help))
        nav.add_widget(Button(text="K", on_press=self.show_camera))
        nav.add_widget(Button(text="G", on_press=self.show_gallery))
        nav.add_widget(Button(text="E", on_press=self.show_extra))

        self.root.add_widget(nav)

        # CONTENT BEREICH
        self.content = FloatLayout()
        self.root.add_widget(self.content)

        self.show_camera()

        return self.root

    # =========================================================
    # ===================== KAMERA ============================
    # =========================================================

    def show_camera(self, *args):

        self.content.clear_widgets()

        # -------------------------------
        # >>>>> HIER IST DIE KAMERA <<<<<
        # -------------------------------

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 0.9)
        self.camera.pos_hint = {"top": 1}

        # =========================================================
        # 🔥🔥🔥 HIER WIRD DIE KAMERA 90° NACH RECHTS GEDREHT 🔥🔥🔥
        # =========================================================
        with self.camera.canvas.before:
            PushMatrix()
            self.rotation = Rotate(
                angle=-90,   # ← HIER WIRD GEDREHT (90° NACH RECHTS)
                origin=self.camera.center
            )

        with self.camera.canvas.after:
            PopMatrix()

        # Rotation dynamisch aktualisieren
        self.camera.bind(pos=self.update_rotation_origin,
                         size=self.update_rotation_origin)

        # =========================================================

        self.content.add_widget(self.camera)

        # Runder weißer Kamera Button
        capture_btn = Button(
            size_hint=(None, None),
            size=(90, 90),
            pos_hint={"center_x": 0.5, "y": 0.02},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )

        capture_btn.bind(on_press=self.take_photo)
        self.content.add_widget(capture_btn)

    def update_rotation_origin(self, *args):
        if hasattr(self, "rotation"):
            self.rotation.origin = self.camera.center

    def take_photo(self, *args):
        try:
            number = self.get_next_number()
            filename = f"{number:04}.png"
            path = os.path.join(self.photos_dir, filename)

            self.camera.export_to_png(path)

            self.store.put(
                str(number),
                name=f"{number:04}",
                date=str(datetime.now())
            )

            self.show_camera()

        except Exception as e:
            print("Fehler beim Speichern:", e)

    def get_next_number(self):
        files = [
            f for f in os.listdir(self.photos_dir)
            if f.endswith(".png")
        ]
        numbers = [int(f.replace(".png", "")) for f in files if f.replace(".png", "").isdigit()]
        return max(numbers)+1 if numbers else 1

    # =========================================================
    # GALLERY
    # =========================================================

    def show_gallery(self, *args):

        self.content.clear_widgets()

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=20, padding=20, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([
            f for f in os.listdir(self.photos_dir)
            if f.endswith(".png")
        ])

        for file in files:
            path = os.path.join(self.photos_dir, file)

            img = Button(
                background_normal=path,
                size_hint_y=None,
                height=350
            )

            grid.add_widget(img)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =========================================================
    # HELP
    # =========================================================

    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(text="Hilfe"))

    # =========================================================
    # EXTRA
    # =========================================================

    def show_extra(self, *args):

        self.content.clear_widgets()

        layout = GridLayout(cols=3, padding=40, spacing=20)

        layout.add_widget(Label(text="Daten von Arduino"))
        ja1 = Button(text="Ja", size_hint=(None,None), size=(100,50))
        nein1 = Button(text="Nein", size_hint=(None,None), size=(100,50))
        layout.add_widget(ja1)
        layout.add_widget(nein1)

        layout.add_widget(Label(text="Mit Winkel"))
        ja2 = Button(text="Ja", size_hint=(None,None), size=(100,50))
        nein2 = Button(text="Nein", size_hint=(None,None), size=(100,50))
        layout.add_widget(ja2)
        layout.add_widget(nein2)

        self.content.add_widget(layout)


if __name__ == "__main__":
    CameraApp().run()
