import os
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
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

        # Startseite abhängig von Kamera-Berechtigung
        if self.check_camera_permission():
            self.show_camera()
        else:
            self.show_help()

        return self.root

    # ========================= Kamera-Berechtigung =========================
    def check_camera_permission(self):
        try:
            cam = Camera(play=True, resolution=(1280, 720))
            cam.play = False
            return True
        except Exception:
            return False

    # ========================= Hilfe =========================
    def show_help(self, *args):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)
        layout.add_widget(Label(text="Hilfe", font_size=30))
        layout.add_widget(Label(text="Willkommen zur Kamera-App!"))
        self.content.add_widget(layout)

    # ========================= Kamera =========================
    def show_camera(self, *args):
        self.content.clear_widgets()

        if not self.check_camera_permission():
            self.content.add_widget(Label(text="Keine Berechtigung verfügbar", font_size=24))
            return

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 0.7)
        self.camera.pos_hint = {"center_y":0.65}

        with self.camera.canvas.before:
            PushMatrix()
            self.rotation = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rotation_origin, size=self.update_rotation_origin)
        self.content.add_widget(self.camera)

        # Runder Kamera-Button
        self.capture_btn = Button(size_hint=(None,None), size=(90,90),
                                  pos_hint={"center_x":0.5, "y":0.02},
                                  background_normal="", background_color=(1,1,1,1))
        self.capture_btn.bind(on_press=self.capture_photo_preview)
        self.content.add_widget(self.capture_btn)

        # Vorschau und Buttons (werden nach Aufnahme angezeigt)
        self.preview_image = None
        self.save_btn = None
        self.retry_btn = None

        # Roter Punkt bei Arduino aktiv
        if self.store.exists("arduino") and self.store.get("arduino")["value"] == "Ja":
            with self.camera.canvas:
                Color(1,0,0,1)
                self.red_dot = Ellipse(pos=(10, self.camera.height-30), size=(20,20))

    def update_rotation_origin(self, *args):
        if hasattr(self, "rotation"):
            self.rotation.origin = self.camera.center

    # ========================= Foto aufnehmen + Vorschau =========================
    def capture_photo_preview(self, *args):
        number = self.get_next_number()
        filename = f"{number:04}.png"
        path = os.path.join(self.photos_dir, filename)
        self.camera.export_to_png(path)

        # Vorschau unter Kamera
        if self.preview_image:
            self.content.remove_widget(self.preview_image)
        self.preview_image = AsyncImage(source=path, size_hint=(1,0.25), pos_hint={"x":0, "y":0.35})
        self.content.add_widget(self.preview_image)

        # Buttons Speichern / Wiederholen unter Vorschau
        if self.save_btn:
            self.content.remove_widget(self.save_btn)
        if self.retry_btn:
            self.content.remove_widget(self.retry_btn)

        self.save_btn = Button(text="Speichern", size_hint=(0.4,0.08), pos_hint={"x":0.05, "y":0.28})
        self.retry_btn = Button(text="Wiederholen", size_hint=(0.4,0.08), pos_hint={"x":0.55, "y":0.28})
        self.content.add_widget(self.save_btn)
        self.content.add_widget(self.retry_btn)

        # Bind Aktionen
        self.save_btn.bind(on_press=lambda x: self.save_photo(path, filename))
        self.retry_btn.bind(on_press=lambda x: self.retry_photo(path))

    def save_photo(self, path, filename):
        # Foto speichern
        self.store.put(str(filename.replace(".png","")),
                       name=filename.replace(".png",""),
                       date=str(datetime.now()),
                       arduino=self.store.get("arduino")["value"] if self.store.exists("arduino") else "Nein")
        self.remove_preview_buttons()
        self.show_gallery()

    def retry_photo(self, path):
        if os.path.exists(path):
            os.remove(path)
        self.remove_preview_buttons()

    def remove_preview_buttons(self):
        if self.preview_image:
            self.content.remove_widget(self.preview_image)
            self.preview_image = None
        if self.save_btn:
            self.content.remove_widget(self.save_btn)
            self.save_btn = None
        if self.retry_btn:
            self.content.remove_widget(self.retry_btn)
            self.retry_btn = None

    def get_next_number(self):
        files = [f for f in os.listdir(self.photos_dir) if f.endswith(".png")]
        numbers = [int(f.replace(".png","")) for f in files if f.replace(".png","").isdigit()]
        return max(numbers)+1 if numbers else 1

    # ========================= Galerie =========================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = BoxLayout(orientation="vertical", spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")],
                       key=lambda x: os.path.getmtime(os.path.join(self.photos_dir, x)), reverse=True)

        if not files:
            self.content.add_widget(Label(text="Noch keine Fotos verfügbar", font_size=24))
            return

        for file in files:
            path = os.path.join(self.photos_dir, file)
            container = BoxLayout(orientation="vertical", size_hint_y=None, height=200, spacing=5)
            img = AsyncImage(source=path, allow_stretch=True, keep_ratio=True)
            container.add_widget(img)

            btn_layout = BoxLayout(size_hint_y=None, height=30)
            btn_layout.add_widget(Label(text=file.replace(".png",""), size_hint_x=0.8))
            info_btn = Button(text="i", size_hint_x=0.2)
            info_btn.bind(on_press=lambda x, p=path, f=file: self.show_image_popup(p, f))
            btn_layout.add_widget(info_btn)
            container.add_widget(btn_layout)

            # Roter Punkt falls Arduino aktiv
            if self.store.exists(file.replace(".png","")):
                data = self.store.get(file.replace(".png",""))
                if data.get("arduino")=="Ja":
                    with img.canvas:
                        Color(1,0,0,1)
                        Ellipse(pos=(5, img.height-25), size=(20,20))

            grid.add_widget(container)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ========================= Bild Popup =========================
    def show_image_popup(self, path, filename):
        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)
        layout.add_widget(AsyncImage(source=path, allow_stretch=True, keep_ratio=True, size_hint_y=0.7))
        layout.add_widget(Label(text=f"Nummer: {filename.replace('.png','')}"))

        popup = Button(text="Schließen", size_hint_y=0.2)
        popup.bind(on_press=lambda x: popup.parent.dismiss() if popup.parent else None)
        layout.add_widget(popup)

        from kivy.uix.popup import Popup as KivyPopup
        KivyPopup(title="Bild", content=layout, size_hint=(0.9,0.9)).open()

    # ========================= Einstellungen =========================
    def show_extra(self, *args):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical", spacing=15, padding=20)
        layout.add_widget(Label(text="Einstellung", font_size=24))

        # Daten von Arduino
        line1 = BoxLayout(spacing=10)
        line1.add_widget(Label(text="Daten von Arduino", size_hint_x=0.5))
        ja1 = Button(text="Ja")
        nein1 = Button(text="Nein")
        line1.add_widget(ja1)
        line1.add_widget(nein1)
        layout.add_widget(line1)

        # Mit Winkel
        line2 = BoxLayout(spacing=10)
        line2.add_widget(Label(text="Mit Winkel", size_hint_x=0.5))
        ja2 = Button(text="Ja")
        nein2 = Button(text="Nein")
        line2.add_widget(ja2)
        line2.add_widget(nein2)
        layout.add_widget(line2)

        def update_button_color(btn_yes, btn_no, value):
            btn_yes.background_color = (0,0.5,0,1) if value=="Ja" else (1,1,1,1)
            btn_no.background_color = (0,0.5,0,1) if value=="Nein" else (1,1,1,1)

        if self.store.exists("arduino"):
            update_button_color(ja1, nein1, self.store.get("arduino")["value"])
        if self.store.exists("winkel"):
            update_button_color(ja2, nein2, self.store.get("winkel")["value"])

        ja1.bind(on_press=lambda x: (self.store.put("arduino", value="Ja"), update_button_color(ja1, nein1, "Ja")))
        nein1.bind(on_press=lambda x: (self.store.put("arduino", value="Nein"), update_button_color(ja1, nein1, "Nein")))
        ja2.bind(on_press=lambda x: (self.store.put("winkel", value="Ja"), update_button_color(ja2, nein2, "Ja")))
        nein2.bind(on_press=lambda x: (self.store.put("winkel", value="Nein"), update_button_color(ja2, nein2, "Nein")))

        self.content.add_widget(layout)


if __name__ == "__main__":
    CameraApp().run()
