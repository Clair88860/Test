import os
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
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Ellipse
from kivy.storage.jsonstore import JsonStore


class CameraApp(App):

    def build(self):
        self.store = JsonStore("settings.json")
        self.photos_dir = "photos"
        if not os.path.exists(self.photos_dir):
            os.makedirs(self.photos_dir)

        self.root = BoxLayout(orientation="vertical")

        # ===== TOP NAVIGATION =====
        nav = BoxLayout(size_hint_y=0.1)
        nav.add_widget(Button(text="?", on_press=self.show_help))
        nav.add_widget(Button(text="K", on_press=self.show_camera))
        nav.add_widget(Button(text="G", on_press=self.show_gallery))
        nav.add_widget(Button(text="E", on_press=self.show_extra))
        self.root.add_widget(nav)

        # ===== CONTENT BEREICH =====
        self.content = FloatLayout()
        self.root.add_widget(self.content)

        self.show_camera()
        return self.root

    # ========================= CAMERA =========================
    def show_camera(self, *args):
        self.content.clear_widgets()

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 0.95)
        self.camera.pos_hint = {"center_y":0.55}

        with self.camera.canvas.before:
            PushMatrix()
            self.rotation = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rotation_origin, size=self.update_rotation_origin)
        self.content.add_widget(self.camera)

        # Runder weißer Button
        capture_btn = Button(size_hint=(None,None), size=(90,90),
                             pos_hint={"center_x":0.5, "y":0.02},
                             background_normal="", background_color=(1,1,1,1))
        capture_btn.bind(on_press=self.take_photo)
        self.content.add_widget(capture_btn)

        # Roter Punkt bei Arduino aktiv
        if self.store.exists("arduino") and self.store.get("arduino")["value"] == "Ja":
            with self.camera.canvas:
                Color(1,0,0,1)
                self.red_dot = Ellipse(pos=(10, self.camera.height-30), size=(20,20))

    def update_rotation_origin(self, *args):
        if hasattr(self, "rotation"):
            self.rotation.origin = self.camera.center

    def take_photo(self, *args):
        try:
            number = self.get_next_number()
            filename = f"{number:04}.png"
            path = os.path.join(self.photos_dir, filename)
            self.camera.export_to_png(path)

            self.store.put(str(number),
                           name=f"{number:04}",
                           date=str(datetime.now()),
                           arduino=self.store.get("arduino")["value"] if self.store.exists("arduino") else "Nein")

            self.show_camera()
        except Exception as e:
            print("Fehler beim Speichern:", e)

    def get_next_number(self):
        files = [f for f in os.listdir(self.photos_dir) if f.endswith(".png")]
        numbers = [int(f.replace(".png", "")) for f in files if f.replace(".png", "").isdigit()]
        return max(numbers)+1 if numbers else 1

    # ========================= GALLERY =========================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=20, padding=20, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted(
            [f for f in os.listdir(self.photos_dir) if f.endswith(".png")],
            key=lambda x: os.path.getmtime(os.path.join(self.photos_dir, x)),
            reverse=True
        )

        for file in files:
            path = os.path.join(self.photos_dir, file)
            btn = Button(size_hint_y=None, height=350, background_normal=path)
            btn.bind(on_press=lambda x, p=path, f=file: self.show_image_popup(p, f))
            grid.add_widget(btn)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    def show_image_popup(self, path, filename):
        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)
        layout.add_widget(AsyncImage(source=path, size_hint_y=0.7))
        layout.add_widget(Label(text=f"Name: {filename}"))

        btn_layout = BoxLayout(size_hint_y=0.2, spacing=10)

        info_btn = Button(text="i")
        info_btn.bind(on_press=lambda x: self.show_info_popup(path, filename))
        btn_layout.add_widget(info_btn)

        layout.add_widget(btn_layout)

        popup = Popup(title="Bild", content=layout, size_hint=(0.9, 0.9))
        popup.open()

    def show_info_popup(self, path, filename):
        layout = GridLayout(cols=2, padding=20, spacing=10)
        layout.add_widget(Label(text="Neuer Name:"))
        name_input = TextInput(text=filename.replace(".png",""))
        layout.add_widget(name_input)

        layout.add_widget(Label(text="Datum & Uhrzeit:"))
        layout.add_widget(Label(text=datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")))

        def rename_photo(instance):
            new_name = name_input.text.strip()
            if new_name:
                new_path = os.path.join(self.photos_dir, f"{new_name}.png")
                os.rename(path, new_path)
                self.show_gallery()
                popup.dismiss()

        rename_btn = Button(text="Umbenennen")
        rename_btn.bind(on_press=rename_photo)
        layout.add_widget(rename_btn)

        def delete_photo(instance):
            os.remove(path)
            self.show_gallery()
            popup.dismiss()

        del_btn = Button(text="Löschen")
        del_btn.bind(on_press=delete_photo)
        layout.add_widget(del_btn)

        popup = Popup(title="Info", content=layout, size_hint=(0.8,0.8))
        popup.open()

    # ========================= HELP =========================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(text="Hilfe"))

    # ========================= SETTINGS =========================
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

        # Lade gespeicherte Werte
        if self.store.exists("arduino"):
            val = self.store.get("arduino")["value"]
            if val=="Ja": ja1.background_color = (0,0.5,0,1)
            else: nein1.background_color = (0,0.5,0,1)
        if self.store.exists("winkel"):
            val = self.store.get("winkel")["value"]
            if val=="Ja": ja2.background_color = (0,0.5,0,1)
            else: nein2.background_color = (0,0.5,0,1)

        def set_arduino(btn_val):
            self.store.put("arduino", value=btn_val)
            self.show_extra()

        def set_winkel(btn_val):
            self.store.put("winkel", value=btn_val)
            self.show_extra()

        ja1.bind(on_press=lambda x: set_arduino("Ja"))
        nein1.bind(on_press=lambda x: set_arduino("Nein"))
        ja2.bind(on_press=lambda x: set_winkel("Ja"))
        nein2.bind(on_press=lambda x: set_winkel("Nein"))

        self.content.add_widget(layout)


if __name__ == "__main__":
    CameraApp().run()
