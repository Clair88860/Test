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
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore


class CameraApp(App):

    def build(self):

        self.store = JsonStore("settings.json")
        self.photos_dir = "photos"

        if not os.path.exists(self.photos_dir):
            os.makedirs(self.photos_dir)

        self.photo_counter = self.get_next_number()

        self.root = BoxLayout(orientation="vertical")

        # -------- TOP NAVIGATION --------
        nav = BoxLayout(size_hint_y=0.1)

        nav.add_widget(Button(text="?", on_press=self.show_help))
        nav.add_widget(Button(text="K", on_press=self.show_camera))
        nav.add_widget(Button(text="G", on_press=self.show_gallery))
        nav.add_widget(Button(text="E", on_press=self.show_extra))

        self.root.add_widget(nav)

        # -------- CONTENT --------
        self.content = FloatLayout()
        self.root.add_widget(self.content)

        self.show_camera()

        Window.bind(on_resize=self.update_orientation)

        return self.root

    # =========================================================
    # CAMERA VIEW
    # =========================================================

    def show_camera(self, *args):

        self.content.clear_widgets()

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 0.9)
        self.camera.pos_hint = {"top": 1}
        self.content.add_widget(self.camera)

        self.update_orientation()

        capture_btn = Button(
            size_hint=(None, None),
            size=(90, 90),
            pos_hint={"center_x": 0.5, "y": 0.02},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )

        capture_btn.bind(on_press=self.take_photo)
        self.content.add_widget(capture_btn)

    def update_orientation(self, *args):
        if hasattr(self, "camera"):
            if Window.height > Window.width:
                self.camera.rotation = -90
            else:
                self.camera.rotation = 0

    def take_photo(self, *args):

        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)

        number = f"{self.photo_counter:04}"
        final_path = os.path.join(self.photos_dir, f"{number}.png")
        shutil.move(temp_path, final_path)

        self.store.put(number, name=number, date=str(datetime.now()))

        self.photo_counter += 1

        self.show_camera()

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

            img.bind(on_press=lambda x, p=path: self.open_image_view(p))
            grid.add_widget(img)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # =========================================================
    # IMAGE VIEW
    # =========================================================

    def open_image_view(self, path):

        self.content.clear_widgets()

        layout = FloatLayout()

        img = AsyncImage(
            source=path,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 0.85),
            pos_hint={"top": 1}
        )
        layout.add_widget(img)

        number = os.path.basename(path).replace(".png", "")

        name = self.store.get(number)["name"] if self.store.exists(number) else number

        bottom = BoxLayout(
            size_hint=(1, 0.15),
            pos_hint={"y": 0}
        )

        name_label = Label(text=name)
        info_btn = Button(text="i", size_hint=(None, 1), width=60)

        info_btn.bind(on_press=lambda x: self.show_info_popup(number, path))

        bottom.add_widget(name_label)
        bottom.add_widget(info_btn)

        layout.add_widget(bottom)

        self.content.add_widget(layout)

    # =========================================================
    # INFO POPUP
    # =========================================================

    def show_info_popup(self, number, path):

        box = BoxLayout(orientation="vertical", spacing=10, padding=20)

        name_input = TextInput(text=self.store.get(number)["name"])
        box.add_widget(name_input)

        date_label = Label(text=self.store.get(number)["date"])
        box.add_widget(date_label)

        rename_btn = Button(text="Speichern")
        delete_btn = Button(text="Foto löschen")

        box.add_widget(rename_btn)
        box.add_widget(delete_btn)

        popup = Popup(title="Info", content=box, size_hint=(0.8, 0.6))

        rename_btn.bind(on_press=lambda x: self.rename_photo(number, name_input.text, popup))
        delete_btn.bind(on_press=lambda x: self.confirm_delete(number, path, popup))

        popup.open()

    def rename_photo(self, number, new_name, popup):
        data = self.store.get(number)
        self.store.put(number, name=new_name, date=data["date"])
        popup.dismiss()
        self.show_gallery()

    def confirm_delete(self, number, path, popup):

        confirm_box = BoxLayout(orientation="vertical")

        confirm_box.add_widget(Label(text="Wirklich löschen?"))

        btns = BoxLayout()
        yes = Button(text="Ja")
        no = Button(text="Nein")

        btns.add_widget(yes)
        btns.add_widget(no)

        confirm_box.add_widget(btns)

        confirm_popup = Popup(title="Sicher?", content=confirm_box, size_hint=(0.7, 0.4))

        yes.bind(on_press=lambda x: self.delete_photo(number, path, popup, confirm_popup))
        no.bind(on_press=confirm_popup.dismiss)

        confirm_popup.open()

    def delete_photo(self, number, path, popup, confirm_popup):
        os.remove(path)
        if self.store.exists(number):
            self.store.delete(number)

        confirm_popup.dismiss()
        popup.dismiss()
        self.show_gallery()

    # =========================================================
    # HELP
    # =========================================================

    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(text="Hilfe"))

    # =========================================================
    # EXTRA MENU
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

        def toggle(key, value, active, inactive):
            active.background_color = (0,1,0,1)
            inactive.background_color = (1,1,1,1)
            self.store.put(key, value=value)

        ja1.bind(on_press=lambda x: toggle("arduino","ja",ja1,nein1))
        nein1.bind(on_press=lambda x: toggle("arduino","nein",nein1,ja1))
        ja2.bind(on_press=lambda x: toggle("winkel","ja",ja2,nein2))
        nein2.bind(on_press=lambda x: toggle("winkel","nein",nein2,ja2))

        self.content.add_widget(layout)


if __name__ == "__main__":
    CameraApp().run()
