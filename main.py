import os
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.camera import Camera
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Ellipse
from kivy.utils import platform

IS_ANDROID = platform == "android"

class MainApp(App):
    def build(self):
        # User-Data-Verzeichnis für Fotos
        self.user_data_dir = App.get_running_app().user_data_dir or os.getcwd()
        os.makedirs(self.user_data_dir, exist_ok=True)

        self.root = BoxLayout(orientation="vertical")

        # ---------------- Dashboard ----------------
        self.dashboard = BoxLayout(size_hint_y=0.1)
        self.btn_camera = Button(text="K"); self.btn_camera.bind(on_press=self.show_camera)
        self.btn_gallery = Button(text="G"); self.btn_gallery.bind(on_press=self.show_gallery)
        self.btn_e = Button(text="E"); self.btn_e.bind(on_press=self.show_e)
        self.btn_a = Button(text="A"); self.btn_a.bind(on_press=self.show_a)
        for b in [self.btn_camera, self.btn_gallery, self.btn_e, self.btn_a]:
            self.dashboard.add_widget(b)
        self.root.add_widget(self.dashboard)

        # ---------------- Content ----------------
        self.content = BoxLayout()
        self.root.add_widget(self.content)

        # E-Seite Einstellungen
        self.arduino_enabled = False
        self.auto_save = False
        self.winkel_enabled = False
        self.zentrierung_enabled = False

        # Kamera-Variable
        self.camera = None
        self.capture_btn = None
        self.rot = None

        # Kamera-Berechtigungen
        if IS_ANDROID:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.CAMERA], self.permissions_callback)
        else:
            Clock.schedule_once(lambda dt: self.show_camera(), 0.1)

        return self.root

    def permissions_callback(self, permissions, results):
        if all(results):
            Clock.schedule_once(lambda dt: self.show_camera(), 0.1)
        else:
            self.content.clear_widgets()
            self.content.add_widget(Label(text="Keine Kameraberechtigung!"))

    # ---------------- Dashboard-Aktualisierung ----------------
    def update_dashboard(self):
        # Nur nötig für spätere Erweiterung (BLE/Nordrichtung)
        pass

    # ---------------- Kamera ----------------
    def show_camera(self, *args):
        self.content.clear_widgets()
        layout = FloatLayout()

        # Kamera
        try:
            self.camera = Camera(play=True, resolution=(1920,1080))
            with self.camera.canvas.before:
                PushMatrix()
                self.rot = Rotate(angle=-90, origin=self.camera.center)
            with self.camera.canvas.after:
                PopMatrix()
            self.camera.bind(pos=self.update_rot, size=self.update_rot)
            layout.add_widget(self.camera)
        except Exception as e:
            layout.add_widget(Label(text=f"Kamera konnte nicht gestartet werden:\n{e}"))

        # Runder Aufnahme-Button
        self.capture_btn = Button(size_hint=(None,None), size=(dp(90), dp(90)),
                                  background_normal="", background_color=(1,1,1,1),
                                  pos_hint={"center_x":0.5,"y":0.02})
        with self.capture_btn.canvas.before:
            Color(1,1,1,1)
            self.circle = Ellipse(size=self.capture_btn.size, pos=self.capture_btn.pos)
        self.capture_btn.bind(pos=self.update_circle, size=self.update_circle)
        self.capture_btn.bind(on_press=self.take_photo)
        layout.add_widget(self.capture_btn)

        self.content.add_widget(layout)

    def update_rot(self, *args):
        if self.rot:
            self.rot.origin = self.camera.center

    def update_circle(self, *args):
        if self.circle and self.capture_btn:
            self.circle.pos = self.capture_btn.pos
            self.circle.size = self.capture_btn.size

    def take_photo(self, instance):
        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])
        number = len(files)+1
        filename = f"{number:04d}.png"
        path = os.path.join(self.user_data_dir, filename)
        self.camera.export_to_png(path)
        self.show_preview(path)

    def show_preview(self, path):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        img = Image(source=path)
        layout.add_widget(img)
        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern"); repeat = Button(text="Wiederholen")
        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save); btns.add_widget(repeat)
        layout.add_widget(btns)
        self.content.add_widget(layout)

    # ---------------- Galerie ----------------
    def show_gallery(self, *args):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])
        for file in files:
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(400))
            lbl = Label(text=file.replace(".png",""), size_hint_y=None, height=dp(30))
            layout.add_widget(lbl)
            img = Image(source=os.path.join(self.user_data_dir, file),
                        size_hint_y=None, height=dp(350),
                        allow_stretch=True, keep_ratio=True)
            img.bind(on_touch_down=lambda inst, touch, f=file: self.open_image(f) if inst.collide_point(*touch.pos) else None)
            layout.add_widget(img)
            grid.add_widget(layout)
        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    def open_image(self, filename):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        img_layout = FloatLayout(size_hint_y=0.8)
        img_path = os.path.join(self.user_data_dir, filename)
        img = Image(source=img_path)
        img_layout.add_widget(img)
        layout.add_widget(img_layout)
        bottom = BoxLayout(size_hint_y=0.15)
        name_lbl = Label(text=filename.replace(".png",""))
        info_btn = Button(text="i", size_hint=(None,None), size=(dp(40),dp(40)))
        info_btn.bind(on_press=lambda x: self.show_info(filename))
        bottom.add_widget(name_lbl); bottom.add_widget(info_btn)
        layout.add_widget(bottom)
        self.content.add_widget(layout)

    def show_info(self, filename):
        path = os.path.join(self.user_data_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10)
        box.add_widget(Label(text=f"Name:"))
        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(name_input)
        box.add_widget(Label(text=f"Datum/Uhrzeit: {datetime.fromtimestamp(os.path.getmtime(path))}"))
        save_btn = Button(text="Name speichern")
        save_btn.bind(on_press=lambda x: self.rename_file(filename, name_input.text))
        box.add_widget(save_btn)
        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.confirm_delete(filename))
        box.add_widget(delete_btn)
        popup = Popup(title=f"Info {filename}", content=box, size_hint=(0.8,0.7))
        popup.open()

    def rename_file(self, old_name, new_name):
        old_path = os.path.join(self.user_data_dir, old_name)
        new_path = os.path.join(self.user_data_dir, f"{new_name}.png")
        os.rename(old_path, new_path)
        self.show_gallery()

    def confirm_delete(self, filename):
        path = os.path.join(self.user_data_dir, filename)
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(text="Wirklich löschen?"))
        yes = Button(text="Ja"); no = Button(text="Nein")
        yes.bind(on_press=lambda x: (os.remove(path), self.show_gallery()))
        no.bind(on_press=lambda x: self.show_gallery())
        box.add_widget(yes); box.add_widget(no)
        popup = Popup(title="Sicher?", content=box, size_hint=(0.7,0.4))
        popup.open()

    # ---------------- A-Seite ----------------
    def show_a(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical")
        if self.arduino_enabled:
            vbox.add_widget(Label(text="Winkel/Nordrichtung wird hier angezeigt"))
        else:
            vbox.add_widget(Label(text="Sie müssen die Daten erst in den Einstellungen aktivieren"))
        self.content.add_widget(vbox)

    # ---------------- E-Seite ----------------
    def show_e(self,*args):
        self.content.clear_widgets()
        vbox = BoxLayout(orientation="vertical", padding=10, spacing=10)
        # Arduino aktiviert
        h1 = BoxLayout()
        h1.add_widget(Label(text="Mit Arduino"))
        ja = ToggleButton(text="Ja", group="arduino")
        nein = ToggleButton(text="Nein", group="arduino", state="down")
        ja.bind(on_press=lambda x: setattr(self,'arduino_enabled', True))
        nein.bind(on_press=lambda x: setattr(self,'arduino_enabled', False))
        h1.add_widget(ja); h1.add_widget(nein)
        vbox.add_widget(h1)
        # Zentrierung
        h2 = BoxLayout(); h2.add_widget(Label(text="Zentrierung"))
        h2.add_widget(ToggleButton(text="Ja", group="zent"))
        h2.add_widget(ToggleButton(text="Nein", group="zent", state="down"))
        vbox.add_widget(h2)
        # Automatisches Speichern
        h3 = BoxLayout(); h3.add_widget(Label(text="Automatisches Speichern"))
        h3.add_widget(ToggleButton(text="Ja", group="auto"))
        h3.add_widget(ToggleButton(text="Nein", group="auto", state="down"))
        vbox.add_widget(h3)
        # Mit Winkel
        h4 = BoxLayout(); h4.add_widget(Label(text="Mit Winkel"))
        h4.add_widget(ToggleButton(text="Ja", group="winkel"))
        h4.add_widget(ToggleButton(text="Nein", group="winkel", state="down"))
        vbox.add_widget(h4)
        self.content.add_widget(vbox)

if __name__ == "__main__":
    MainApp().run()
