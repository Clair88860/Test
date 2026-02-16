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
    # Dashboard / Topbar
    # =====================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1}, spacing=5, padding=5)
        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a)
        ]:
            b = Button(text=t, background_normal="", background_color=(0.15,0.15,0.15,1), color=(1,1,1,1))
            b.bind(on_press=f)
            self.topbar.add_widget(b)
        self.add_widget(self.topbar)

    # =====================================================
    # Kamera
    # =====================================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920,1080))
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

    # =====================================================
    # Runder Kamera Button
    # =====================================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None), size=(dp(100),dp(100)),
                              pos_hint={"center_x":0.5,"y":0.04},
                              background_normal="", background_color=(0,0,0,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.outer_circle = Ellipse(size=self.capture.size, pos=self.capture.pos)
            Color(0.9,0.9,0.9,1)
            self.inner_circle = Ellipse(size=(dp(75),dp(75)),
                                        pos=(self.capture.x+dp(12.5), self.capture.y+dp(12.5)))
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size
        self.inner_circle.pos = (self.capture.x+dp(12.5), self.capture.y+dp(12.5))

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(text="Kamera Berechtigung fehlt", pos_hint={"center_x":0.5,"center_y":0.5}))
            return
        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # Fotoaufnahme + Vorschau
    # =====================================================
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number+".png")
        self.camera.export_to_png(path)
        self.show_preview(path)

    def show_preview(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical")
        img = Image(source=path)
        layout.add_widget(img)
        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern"); repeat = Button(text="Wiederholen")
        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save); btns.add_widget(repeat)
        layout.add_widget(btns)
        self.add_widget(layout)

    # =====================================================
    # Galerie
    # =====================================================
    def show_gallery(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        for file in files:
            layout = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(400))
            lbl = Label(text=file.replace(".png",""), size_hint_y=None, height=dp(30))
            layout.add_widget(lbl)
            img = Image(source=os.path.join(self.photos_dir,file), size_hint_y=None, height=dp(350),
                        allow_stretch=True, keep_ratio=True)
            img.bind(on_touch_down=lambda inst,touch,f=file: self.open_image(f) if inst.collide_point(*touch.pos) else None)
            layout.add_widget(img)
            grid.add_widget(layout)
        scroll.add_widget(grid)
        self.add_widget(scroll)

    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical")
        img_layout = FloatLayout(size_hint_y=0.8)
        img_path = os.path.join(self.photos_dir, filename)
        img = Image(source=img_path)
        img_layout.add_widget(img)
        layout.add_widget(img_layout)
        bottom = BoxLayout(size_hint_y=0.15)
        name_lbl = Label(text=filename.replace(".png",""))
        info_btn = Button(text="i", size_hint=(None,None), size=(dp(40),dp(40)))
        info_btn.bind(on_press=lambda x:self.show_info(filename))
        bottom.add_widget(name_lbl); bottom.add_widget(info_btn)
        layout.add_widget(bottom)
        self.add_widget(layout)

    def show_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10)
        box.add_widget(Label(text="Name:"))
        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(name_input)
        box.add_widget(Label(text=f"Datum/Uhrzeit: {datetime.datetime.fromtimestamp(os.path.getmtime(path))}"))
        save_btn = Button(text="Name speichern")
        save_btn.bind(on_press=lambda x:self.rename_file(filename,name_input.text))
        box.add_widget(save_btn)
        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x:self.confirm_delete(filename))
        box.add_widget(delete_btn)
        popup = Popup(title=f"Info {filename}", content=box, size_hint=(0.8,0.7))
        popup.open()

    def rename_file(self, old_name, new_name):
        old_path = os.path.join(self.photos_dir, old_name)
        new_path = os.path.join(self.photos_dir, f"{new_name}.png")
        os.rename(old_path,new_path)
        self.show_gallery()

    def confirm_delete(self, filename):
        path = os.path.join(self.photos_dir, filename)
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(text="Wirklich löschen?"))
        yes = Button(text="Ja"); no = Button(text="Nein")
        yes.bind(on_press=lambda x: (os.remove(path), self.show_gallery()))
        no.bind(on_press=lambda x: self.show_gallery())
        box.add_widget(yes); box.add_widget(no)
        popup = Popup(title="Sicher?", content=box, size_hint=(0.7,0.4))
        popup.open()

    # =====================================================
    # Einstellungen (E-Seite)
    # =====================================================
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical", padding=[20,120,20,20], spacing=20)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None, height=dp(60)))
        def create_toggle_row(text,key):
            row = BoxLayout(size_hint_y=None, height=dp(60))
            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(80),dp(45)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(80),dp(45)))
            value = self.store.get(key)["value"] if self.store.exists(key) else False
            def update(selected):
                if selected:
                    btn_ja.background_color=(0,0.6,0,1); btn_nein.background_color=(1,1,1,1)
                else:
                    btn_nein.background_color=(0,0.6,0,1); btn_ja.background_color=(1,1,1,1)
            update(value)
            btn_ja.bind(on_press=lambda x:[self.store.put(key,value=True),update(True)])
            btn_nein.bind(on_press=lambda x:[self.store.put(key,value=False),update(False)])
            row.add_widget(label); row.add_widget(btn_ja); row.add_widget(btn_nein)
            return row
        layout.add_widget(create_toggle_row("Mit Arduino Daten","arduino"))
        layout.add_widget(create_toggle_row("Mit Winkel","winkel"))
        layout.add_widget(create_toggle_row("Automatisch speichern","auto"))
        self.add_widget(layout)

    # =====================================================
    # A-Seite
    # =====================================================
    def show_a(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        label_text = "Winkel/Nordrichtung wird hier angezeigt" if arduino_on else "Sie müssen die Daten erst in den Einstellungen aktivieren"
        self.add_widget(Label(text=label_text, font_size=24, pos_hint={"center_x":0.5,"center_y":0.5}))


class MainApp(App):
    def build(self):
        return Dashboard()

if __name__=="__main__":
    MainApp().run()
