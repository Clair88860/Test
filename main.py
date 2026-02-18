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
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None

from PIL import Image as PILImage

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
    # DASHBOARD
    # =====================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1}, spacing=5, padding=5)
        for t, f in [("K", self.show_camera), ("G", self.show_gallery),
                     ("E", self.show_settings), ("A", self.show_a), ("H", self.show_help)]:
            b = Button(text=t, background_normal="", background_color=(0.15,0.15,0.15,1), color=(1,1,1,1))
            b.bind(on_press=f)
            self.topbar.add_widget(b)
        self.add_widget(self.topbar)

    # =====================================================
    # KAMERA
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

        # Rahmen nur anzeigen, wenn Entzerrung aktiviert
        if self.store.exists("entzerrung") and self.store.get("entzerrung")["value"]:
            with self.camera.canvas:
                Color(1,0,0,0.6)
                cam_w, cam_h = self.camera.size
                self.frame_width = cam_w * 0.8
                self.frame_height = cam_h * 0.5
                self.frame_rect = Rectangle(pos=(self.camera.center_x - self.frame_width/2,
                                                 self.camera.center_y - self.frame_height/2),
                                            size=(self.frame_width,self.frame_height))
            self.camera.bind(pos=self.update_frame, size=self.update_frame)

    def update_frame(self, *args):
        self.frame_rect.pos = (self.camera.center_x - self.frame_width/2,
                               self.camera.center_y - self.frame_height/2)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # =====================================================
    # Kleiner Kamera Button
    # =====================================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None), size=(dp(70),dp(70)), pos_hint={"center_x": .5,"y": .04},
                              background_normal="", background_color=(0,0,0,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.outer_circle = Ellipse(size=self.capture.size, pos=self.capture.pos)
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(text="Kamera Berechtigung fehlt", pos_hint={"center_x": .5,"center_y": .5}))
            return
        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # FOTO
    # =====================================================
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)

        # Entzerrung aktiv -> Vorschau mit Auswahl
        if self.store.exists("entzerrung") and self.store.get("entzerrung")["value"]:
            self.show_point_selection(path)
        else:
            auto = self.store.get("auto")["value"] if self.store.exists("auto") else False
            if not auto:
                self.show_preview(path)

    def show_point_selection(self, path):
        # Einfacher Platzhalter: Benutzer soll 4 Punkte wählen, hier simuliert
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical")
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        info = Label(text="Wähle 4 Punkte auf dem Bild (Platzhalter)", size_hint_y=None, height=dp(40))
        layout.add_widget(info)

        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")

        # Platzhalter: direkt speichern ohne echte Punkteauswahl
        def save_crop(x):
            # Einfach den Rahmen nutzen
            if hasattr(self, 'frame_rect'):
                img_pil = PILImage.open(path)
                cam_w, cam_h = self.camera.size
                scale_x = img_pil.width / cam_w
                scale_y = img_pil.height / cam_h
                x0,y0 = self.frame_rect.pos
                w,h = self.frame_rect.size
                crop_box = (int(x0*scale_x), int((cam_h-(y0+h))*scale_y),
                            int((x0+w)*scale_x), int((cam_h-y0)*scale_y))
                cropped = img_pil.crop(crop_box)
                cropped.save(path)
            self.show_preview(path)

        save.bind(on_press=save_crop)
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save)
        btns.add_widget(repeat)
        layout.add_widget(btns)
        self.add_widget(layout)

    def show_preview(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical")
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)
        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")
        save.bind(on_press=lambda x: self.show_camera())
        repeat.bind(on_press=lambda x: self.show_camera())
        btns.add_widget(save)
        btns.add_widget(repeat)
        layout.add_widget(btns)
        self.add_widget(layout)

    # =====================================================
    # GALERIE
    # =====================================================
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        if not files:
            self.add_widget(Label(text="Es wurden noch keine Fotos gemacht", font_size=24, pos_hint={"center_x":.5,"center_y":.5}))
            return
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=[10,120,10,10], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for file in files:
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(280), spacing=5)
            img = Image(source=os.path.join(self.photos_dir,file), allow_stretch=True)
            img.bind(on_touch_down=lambda inst,touch,f=file:self.open_image(f) if inst.collide_point(*touch.pos) else None)
            name = Label(text=file.replace(".png",""), size_hint_y=None, height=dp(25))
            box.add_widget(img)
            box.add_widget(name)
            grid.add_widget(box)
        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # EINZELANSICHT / INFO / REST bleibt unverändert
    # =====================================================
    # … Hier bleiben alle bisherigen Funktionen wie open_image, show_info, rename_file etc. unverändert

# =====================================================
# APP
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
