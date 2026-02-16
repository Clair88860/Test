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
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Ellipse, Color
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

        self.build_camera()
        self.build_topbar()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.3)

    # =====================================================
    # Kamera
    # =====================================================

    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920, 1080))
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"center_x": .5, "center_y": .46}

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
            self.circle = Ellipse(size=self.capture.size,
                                  pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle,
                          size=self.update_circle)

        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    # =====================================================
    # Topbar
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08),
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

    # =====================================================
    # Kamera anzeigen
    # =====================================================

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        if check_permission and not check_permission(Permission.CAMERA):
            msg = Label(
                text="Noch keine Berechtigung verfügbar,\nschauen Sie für Hilfe bei der Hilfe Option",
                halign="center",
                pos_hint={"center_x": .5, "center_y": .5}
            )
            self.add_widget(msg)
            return

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # Foto
    # =====================================================

    def take_photo(self, instance):
        path = os.path.join(self.photos_dir,
                            datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
        self.camera.export_to_png(path)

    # =====================================================
    # Galerie
    # =====================================================

    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1, .92),
                            pos_hint={"y": 0})
        grid = GridLayout(cols=3,
                          spacing=10,
                          padding=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted(os.listdir(self.photos_dir))

        for file in files:
            if not file.endswith(".png"):
                continue

            layout = BoxLayout(orientation="vertical",
                               size_hint_y=None,
                               height=dp(140))

            num = Label(text=file.split("_")[0],
                        size_hint_y=.2)
            layout.add_widget(num)

            img = Image(source=os.path.join(self.photos_dir, file),
                        allow_stretch=True,
                        keep_ratio=True)
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

        img = Image(source=path,
                    allow_stretch=True,
                    keep_ratio=True)
        img_layout.add_widget(img)

        if self.store.exists("arduino") and self.store.get("arduino")["value"]:
            north = Label(text="Norden",
                          pos_hint={"right": .98, "top": .98})
            img_layout.add_widget(north)

        layout.add_widget(img_layout)

        bottom = BoxLayout(size_hint_y=.2)

        name = Label(text=filename)

        info = Button(size_hint=(None, None),
                      size=(dp(40), dp(40)),
                      background_normal="",
                      background_color=(1, 1, 1, 0))

        with info.canvas.before:
            Color(1, 1, 1, 1)
            Ellipse(pos=info.pos, size=info.size)

        info.bind(on_press=lambda x:
                  self.image_info(filename))

        bottom.add_widget(name)
        bottom.add_widget(info)

        layout.add_widget(bottom)

        self.add_widget(layout)

    # =====================================================
    # Bild Info Popup
    # =====================================================

    def image_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        stat = os.stat(path)
        dt = datetime.datetime.fromtimestamp(stat.st_mtime)

        box = BoxLayout(orientation="vertical", spacing=10)

        name_input = TextInput(text=filename,
                               multiline=False)
        box.add_widget(name_input)

        box.add_widget(Label(text=str(dt)))

        delete = Button(text="Foto löschen")

        def delete_file(instance):
            os.remove(path)
            popup.dismiss()
            self.show_gallery()

        delete.bind(on_press=delete_file)

        box.add_widget(delete)

        popup = Popup(title="Bildinformationen",
                      content=box,
                      size_hint=(.8, .6))
        popup.open()

    # =====================================================
    # Einstellungen
    # =====================================================

    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=15,
                           pos_hint={"top": .95})

        layout.add_widget(Label(text="Einstellungen",
                                font_size=28,
                                size_hint_y=None,
                                height=dp(50)))

        for text in [
            "Mit Arduino Daten",
            "Mit Winkel",
            "Automatisches Speichern"
        ]:
            row = BoxLayout(size_hint_y=None,
                            height=dp(40))

            row.add_widget(Label(text=text))

            for val in [True, False]:
                btn = Button(text="Ja" if val else "Nein",
                             size_hint=(None, None),
                             size=(dp(60), dp(35)))

                row.add_widget(btn)

            layout.add_widget(row)

        for i in range(5):
            warn = BoxLayout(size_hint_y=None,
                             height=dp(30))
            warn.add_widget(Label(text="!",
                                  color=(0, 0, 0, 1),
                                  size_hint_x=None,
                                  width=dp(20)))
            warn.add_widget(Label(text="Hinweis"))
            layout.add_widget(warn)

        self.add_widget(layout)

    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(Label(text="Hilfe"))
        self.add_widget(self.topbar)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
