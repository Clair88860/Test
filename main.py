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
        os.makedirs(self.photos_dir, exist_ok=True)

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
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1})

        for t, f in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_arduino)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

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
            size=(dp(90), dp(90)),
            pos_hint={"center_x": .5, "y": .02},
            background_normal="",
            background_color=(1, 1, 1, 1)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture.size, pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(
                text="Berechtigung fehlt",
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # Foto
    # =====================================================

    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False

        if auto:
            self.camera.export_to_png(path)
        else:
            content = BoxLayout(orientation="vertical", spacing=10)
            content.add_widget(Label(text="Foto speichern?"))

            btns = BoxLayout()

            save = Button(text="Speichern")
            repeat = Button(text="Wiederholen")

            def save_photo(x):
                self.camera.export_to_png(path)
                popup.dismiss()

            def close_popup(x):
                popup.dismiss()

            save.bind(on_press=save_photo)
            repeat.bind(on_press=close_popup)

            btns.add_widget(save)
            btns.add_widget(repeat)
            content.add_widget(btns)

            popup = Popup(title="Speichern", content=content, size_hint=(.7,.4))
            popup.open()

    # =====================================================
    # Galerie
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1,.92), pos_hint={"y":0})
        grid = GridLayout(cols=3, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        for file in files:
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150))

            num = Label(text=file.replace(".png",""), size_hint_y=.2)
            layout.add_widget(num)

            img = Image(source=os.path.join(self.photos_dir, file))
            img.reload()

            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)

            layout.add_widget(img)
            grid.add_widget(layout)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # Einzelbild
    # =====================================================

    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        path = os.path.join(self.photos_dir, filename)

        layout = BoxLayout(orientation="vertical")

        img_layout = FloatLayout(size_hint_y=.8)
        img = Image(source=path)
        img_layout.add_widget(img)

        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            north = Label(text="Norden",
                          pos_hint={"right": .98, "top": .98})
            img_layout.add_widget(north)

        layout.add_widget(img_layout)

        bottom = BoxLayout(size_hint_y=.15)

        number_label = Label(text=filename.replace(".png",""))

        info = Button(text="i",
                      size_hint=(None,None),
                      size=(dp(40),dp(40)),
                      background_normal="",
                      background_color=(0,0,0,0))

        info.bind(on_press=lambda x: self.image_info(filename))

        bottom.add_widget(number_label)
        bottom.add_widget(info)

        layout.add_widget(bottom)
        self.add_widget(layout)

    # =====================================================
    # Popup
    # =====================================================

    def image_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        stat = os.stat(path)
        dt = datetime.datetime.fromtimestamp(stat.st_mtime)

        box = BoxLayout(orientation="vertical", spacing=10)

        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(name_input)

        box.add_widget(Label(text=str(dt)))

        save_name = Button(text="Name speichern")

        def rename_file(instance):
            new_name = name_input.text + ".png"
            new_path = os.path.join(self.photos_dir, new_name)
            os.rename(path, new_path)
            popup.dismiss()
            self.show_gallery()

        save_name.bind(on_press=rename_file)
        box.add_widget(save_name)

        delete = Button(text="Foto löschen")

        def confirm_delete(instance):
            confirm_box = BoxLayout(orientation="vertical", spacing=10)
            confirm_box.add_widget(Label(text="Wirklich löschen?"))

            yes = Button(text="Ja")
            no = Button(text="Nein")

            def delete_file(x):
                os.remove(path)
                confirm_popup.dismiss()
                popup.dismiss()
                self.show_gallery()

            yes.bind(on_press=delete_file)
            no.bind(on_press=lambda x: confirm_popup.dismiss())

            confirm_box.add_widget(yes)
            confirm_box.add_widget(no)

            confirm_popup = Popup(title="Sicher?", content=confirm_box, size_hint=(.7,.4))
            confirm_popup.open()

        delete.bind(on_press=confirm_delete)
        box.add_widget(delete)

        popup = Popup(title="Info", content=box, size_hint=(.8,.7))
        popup.open()

    # =====================================================
    # Einstellungen
    # =====================================================

    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=20, spacing=15)

        layout.add_widget(Label(text="Einstellungen", font_size=36,
                                size_hint_y=None, height=dp(60)))

        def create_toggle_row(text, key):

            row = BoxLayout(size_hint_y=None, height=dp(50))

            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(70),dp(40)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(70),dp(40)))

            value = self.store.get(key)["value"] if self.store.exists(key) else False

            def update_buttons(selected):
                if selected:
                    btn_ja.background_color = (0,0.5,0,1)
                    btn_nein.background_color = (1,1,1,1)
                else:
                    btn_nein.background_color = (0,0.5,0,1)
                    btn_ja.background_color = (1,1,1,1)

            update_buttons(value)

            btn_ja.bind(on_press=lambda x: [self.store.put(key,value=True), update_buttons(True)])
            btn_nein.bind(on_press=lambda x: [self.store.put(key,value=False), update_buttons(False)])

            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)

            return row

        layout.add_widget(create_toggle_row("Mit Arduino Daten", "arduino"))
        layout.add_widget(create_toggle_row("Mit Winkel", "winkel"))
        layout.add_widget(create_toggle_row("Automatisches Speichern", "auto"))

        layout.add_widget(Label(text="Hinweis: Einstellungen werden gespeichert", color=(0,0,0,1)))
        layout.add_widget(Label(text="Hinweis: Arduino aktiviert Norden Anzeige", color=(0,0,0,1)))
        layout.add_widget(Label(text="Hinweis: Auto Speichern überspringt Abfrage", color=(0,0,0,1)))

        self.add_widget(layout)

    # =====================================================
    # Arduino
    # =====================================================

    def show_arduino(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=20)
        layout.add_widget(Label(text="Arduino Daten", font_size=28))
        self.add_widget(layout)

    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe"))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
