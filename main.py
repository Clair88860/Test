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

        self.store = JsonStore("app_settings.json")
        self.photos_dir = os.path.join(App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # Topbar
        self.topbar = BoxLayout(size_hint=(1, 0.1))
        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra),
            ("A", self.show_arduino)
        ]:
            btn = Button(text=text)
            btn.bind(on_press=func)
            self.topbar.add_widget(btn)
        self.add_widget(self.topbar)

        # Content
        self.content = FloatLayout()
        self.add_widget(self.content)

        # Bottom (Kamera Button)
        self.bottom = FloatLayout(size_hint=(1, 0.18))
        self.add_widget(self.bottom)
        self.create_capture_button()

        # Kamera Seite immer zuerst
        self.show_camera()

    # ================= CAMERA =================
    def create_capture_button(self):
        self.capture_button = Button(
            size_hint=(None,None),
            size=(dp(60),dp(60)),
            background_normal="",
            background_color=(0,0,0,0),
            pos_hint={"center_x":0.5,"y":0.15}
        )
        with self.capture_button.canvas.before:
            Color(1,1,1,1)
            self.circle = Ellipse(size=self.capture_button.size, pos=self.capture_button.pos)
        self.capture_button.bind(pos=self.update_circle, size=self.update_circle)
        self.capture_button.bind(on_press=self.take_photo)
        self.bottom.add_widget(self.capture_button)

    def update_circle(self, *args):
        self.circle.pos = self.capture_button.pos
        self.circle.size = self.capture_button.size

    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom.opacity = 1

        self.camera = Camera(play=True, resolution=(1280,720))
        self.camera.size_hint = (1,1)
        self.camera.pos_hint = {"center_x":0.5,"center_y":0.5}

        try:
            # Kamera wird gedreht -90°
            self.camera.rotation = -90
        except:
            # Falls Kamera nicht verfügbar
            label = Label(text="Berechtigung fehlt", font_size=32)
            self.content.add_widget(label)

        self.content.add_widget(self.camera)

    def take_photo(self, instance):
        files = [f for f in os.listdir(self.photos_dir) if f.endswith(".png")]
        filename = f"{len(files)+1:04d}.png"
        path = os.path.join(self.photos_dir, filename)
        if hasattr(self, "camera"):
            self.camera.export_to_png(path)

    # ================= GALERIE =================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = GridLayout(cols=3, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        for file in files:
            path = os.path.join(self.photos_dir, file)
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=200)

            img_btn = Button(background_normal=path, size_hint_y=0.85)
            img_btn.bind(on_press=lambda x,f=file: self.open_image(f))
            layout.add_widget(img_btn)

            bottom = BoxLayout(size_hint_y=0.15)
            lbl = Label(text=file.replace(".png",""), size_hint_x=0.8)
            info_btn = Button(text="i", size_hint=(None,None), size=(dp(30),dp(30)))
            info_btn.bind(on_press=lambda x,f=file: self.show_image_info(f))
            bottom.add_widget(lbl)
            bottom.add_widget(info_btn)
            layout.add_widget(bottom)

            grid.add_widget(layout)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ================= EINZELANSICHT =================
    def open_image(self, filename):
        self.content.clear_widgets()
        layout = FloatLayout()
        self.content.add_widget(layout)

        path = os.path.join(self.photos_dir, filename)
        img = Image(source=path, allow_stretch=True, keep_ratio=True)
        layout.add_widget(img)

        # Norden Text falls Arduino-Daten aktiv
        if self.store.exists("arduino_data") and self.store.get("arduino_data")["value"]:
            norden_lbl = Label(text="Norden", pos_hint={"right":0.98,"top":0.98}, color=(1,1,1,1))
            layout.add_widget(norden_lbl)

        # Unter Bild: Nummer + i Button
        bottom = BoxLayout(size_hint=(1,0.1), pos_hint={"x":0,"y":0})
        lbl = Label(text=filename.replace(".png",""), size_hint_x=0.8)
        info_btn = Button(text="i", size_hint=(None,None), size=(dp(30),dp(30)))
        info_btn.bind(on_press=lambda x: self.show_image_info(filename))
        bottom.add_widget(lbl)
        bottom.add_widget(info_btn)
        layout.add_widget(bottom)

    # ================= POPUP IMAGE INFO =================
    def show_image_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        layout.add_widget(name_input)

        dt_lbl = Label(text=datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d.%m.%Y %H:%M:%S"))
        layout.add_widget(dt_lbl)

        del_btn = Button(text="Foto löschen", background_color=(1,0,0,1))
        layout.add_widget(del_btn)

        popup = Popup(title="Bild Info", content=layout, size_hint=(0.8,0.6))

        def save_name(instance):
            new_name = name_input.text.strip()
            if new_name:
                new_path = os.path.join(self.photos_dir, new_name+".png")
                os.rename(path, new_path)
                popup.dismiss()
                self.show_gallery()
        name_input.bind(on_text_validate=save_name)

        def delete_photo(instance):
            if os.path.exists(path):
                os.remove(path)
            popup.dismiss()
            self.show_gallery()
        del_btn.bind(on_press=delete_photo)

        popup.open()

    # ================= SEITE E =================
    def show_extra(self, *args):
        self.content.clear_widgets()
        layout = GridLayout(cols=2, spacing=10, padding=20)

        lbl = Label(text="Einstellungen", font_size=32)
        layout.add_widget(lbl)
        layout.add_widget(Label())

        lbl2 = Label(text="Mit Arduino Daten")
        layout.add_widget(lbl2)
        ja_btn = Button(text="Ja", background_color=(0,1,0,1))
        nein_btn = Button(text="Nein")
        layout.add_widget(ja_btn)
        layout.add_widget(nein_btn)

        lbl3 = Label(text="Mit Winkel")
        layout.add_widget(lbl3)
        ja_w = Button(text="Ja", background_color=(0,1,0,1))
        nein_w = Button(text="Nein")
        layout.add_widget(ja_w)
        layout.add_widget(nein_w)

        lbl4 = Label(text="Automatisches Speichern")
        layout.add_widget(lbl4)
        ja_s = Button(text="Ja", background_color=(0,1,0,1))
        nein_s = Button(text="Nein")
        layout.add_widget(ja_s)
        layout.add_widget(nein_s)

        self.content.add_widget(layout)

    # ================= SEITE A =================
    def show_arduino(self, *args):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(Label(text="Arduino Daten Hinweis", font_size=20))
        self.content.add_widget(layout)

    # ================= HELP =================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.content.add_widget(Label(text="Hilfe", font_size=32, pos_hint={"center_x":0.5,"center_y":0.5}))

class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
