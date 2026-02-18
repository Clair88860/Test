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
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate, Line
from kivy.metrics import dp
from kivy.clock import Clock

import cv2
import numpy as np

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

        self.frame_points = None
        self.entzerrung_on = self.store.get("winkel")["value"] if self.store.exists("winkel") else False

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
        self.topbar = BoxLayout(
            size_hint=(1, .08),
            pos_hint={"top": 1},
            spacing=5,
            padding=5
        )

        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a),
            ("H", self.show_help)
        ]:
            b = Button(
                text=t,
                background_normal="",
                background_color=(0.15, 0.15, 0.15, 1),
                color=(1, 1, 1, 1)
            )
            b.bind(on_press=f)
            self.topbar.add_widget(b)

        self.add_widget(self.topbar)

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
        Clock.schedule_interval(self.update_camera_frame, 1/15)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={"center_x": .5, "y": .04},
            background_normal="",
            background_color=(0, 0, 0, 0)
        )

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.outer_circle = Ellipse(size=self.capture.size,
                                        pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(
                text="Kamera Berechtigung fehlt",
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        self.entzerrung_on = self.store.get("winkel")["value"] if self.store.exists("winkel") else False

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # =====================================================
    # Live-Scan-Rahmen
    # =====================================================
    def update_camera_frame(self, dt):
        if not self.entzerrung_on:
            self.camera.canvas.after.clear()
            return

        if not hasattr(self.camera, 'texture') or self.camera.texture is None:
            return

        tex = self.camera.texture
        arr = np.frombuffer(tex.pixels, np.uint8)
        arr = arr.reshape(tex.height, tex.width, 4)
        frame = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        edges = cv2.Canny(blur, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_area = 0
        max_cnt = None
        for cnt in contours:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                if area > max_area:
                    max_area = area
                    max_cnt = approx

        self.frame_points = None
        self.camera.canvas.after.clear()
        if max_cnt is not None:
            h_ratio = self.camera.height / frame.shape[0]
            w_ratio = self.camera.width / frame.shape[1]
            pts = [(pt[0][0]*w_ratio, self.camera.height - pt[0][1]*h_ratio) for pt in max_cnt]
            self.frame_points = pts

            with self.camera.canvas.after:
                Color(0, 1, 0, 0.7)
                Line(points=[*pts[0], *pts[1], *pts[2], *pts[3], *pts[0]], width=2)

    # =====================================================
    # Foto
    # =====================================================
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)

        if self.entzerrung_on and self.frame_points is not None:
            img = cv2.imread(path)
            h, w = img.shape[:2]
            pts_src = np.array([[pt[0]*img.shape[1]/self.camera.width, (self.camera.height-pt[1])*img.shape[0]/self.camera.height] for pt in self.frame_points], dtype='float32')
            pts_dst = np.array([[0,0],[w,0],[w,h],[0,h]], dtype='float32')
            M = cv2.getPerspectiveTransform(pts_src, pts_dst)
            dst = cv2.warpPerspective(img, M, (w,h))
            cv2.imwrite(path, dst)

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False
        if not auto:
            self.show_preview(path)

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
    # Galerie
    # =====================================================
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        if not files:
            self.add_widget(Label(
                text="Es wurden noch keine Fotos gemacht",
                font_size=24,
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        scroll = ScrollView()
        grid = GridLayout(
            cols=2,
            spacing=10,
            padding=[10, 120, 10, 10],
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(280),
                spacing=5
            )

            img = Image(
                source=os.path.join(self.photos_dir, file),
                allow_stretch=True
            )
            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)

            name = Label(
                text=file.replace(".png", ""),
                size_hint_y=None,
                height=dp(25)
            )

            box.add_widget(img)
            box.add_widget(name)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # =====================================================
    # Einzelansicht
    # =====================================================
    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")
        img_layout = FloatLayout(size_hint_y=0.85)

        path = os.path.join(self.photos_dir, filename)
        img = Image(source=path, allow_stretch=True)
        img_layout.add_widget(img)
        layout.add_widget(img_layout)

        bottom = BoxLayout(orientation="vertical", size_hint_y=0.15, spacing=5)
        name_lbl = Label(text=filename.replace(".png", ""), size_hint_y=None, height=dp(25))
        info_btn = Button(text="i", size_hint=(None, None), size=(dp(40), dp(40)))
        info_btn.bind(on_press=lambda x: self.show_info(filename))

        row = BoxLayout()
        row.add_widget(name_lbl)
        row.add_widget(info_btn)
        bottom.add_widget(row)
        layout.add_widget(bottom)
        self.add_widget(layout)

    # =====================================================
    # Info-Popup
    # =====================================================
    def show_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        name_input = TextInput(text=filename.replace(".png", ""), multiline=False)
        box.add_widget(Label(text="Name ändern:"))
        box.add_widget(name_input)

        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        box.add_widget(Label(text=f"Datum/Uhrzeit:\n{timestamp}"))

        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        if arduino_on:
            box.add_widget(Label(text="Norden", color=(1,0,0,1), font_size=20))

        save_btn = Button(text="Speichern")
        save_btn.bind(on_press=lambda x: self.rename_file(filename, name_input.text))
        box.add_widget(save_btn)

        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.delete_file_safe(filename))
        box.add_widget(delete_btn)

        popup = Popup(title=filename.replace(".png",""), content=box, size_hint=(0.8,0.7))
        popup.open()

    def delete_file_safe(self, filename):
        try:
            path = os.path.join(self.photos_dir, filename)
            os.remove(path)
        except Exception as e:
            print("Fehler beim Löschen:", e)
        finally:
            self.show_gallery()

    def rename_file(self, old_name, new_name):
        old_path = os.path.join(self.photos_dir, old_name)
        new_path = os.path.join(self.photos_dir, f"{new_name}.png")
        os.rename(old_path, new_path)
        self.show_gallery()

    # =====================================================
    # Seiten A/H
    # =====================================================
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        text = "Hier werden später die Arduino Daten angezeigt." if arduino_on else "Sie müssen die Daten erst in den Einstellungen aktivieren"
        self.add_widget(Label(text=text, font_size=24, pos_hint={"center_x": .5, "center_y": .5}))

    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Bei Fragen oder Problemen: E-Mail kontaktieren", font_size=20, pos_hint={"center_x": .5, "center_y": .5}))

    # =====================================================
    # Einstellungen
    # =====================================================
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=[20,120,20,20], spacing=20)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None, height=dp(60)))

        def create_toggle_row(text, key):
            row = BoxLayout(size_hint_y=None, height=dp(60))
            label = Label(text=text)

            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(80),dp(45)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(80),dp(45)))
            value = self.store.get(key)["value"] if self.store.exists(key) else False

            def update(selected):
                if selected:
                    btn_ja.background_color=(0,0.6,0,1)
                    btn_nein.background_color=(1,1,1,1)
                else:
                    btn_nein.background_color=(0,0.6,0,1)
                    btn_ja.background_color=(1,1,1,1)
            update(value)

            btn_ja.bind(on_press=lambda x:[self.store.put(key,value=True), update(True)])
            btn_nein.bind(on_press=lambda x:[self.store.put(key,value=False), update(False)])

            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row

        layout.add_widget(create_toggle_row("Mit Arduino Daten","arduino"))
        layout.add_widget(create_toggle_row("Mit Winkel","winkel"))
        layout.add_widget(create_toggle_row("Automatisch speichern","auto"))
        self.add_widget(layout)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
