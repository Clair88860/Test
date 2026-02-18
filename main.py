import os
import datetime
import traceback
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
from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

import cv2
import numpy as np

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None

# =====================================================
# Draggable Eckpunkte für Entzerrung
# =====================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (40, 40)
        with self.canvas.before:
            Color(0, 1, 0, 0.6)
            self.circle = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.update_circle, size=self.update_circle)

    def update_circle(self, *args):
        self.circle.pos = self.pos
        self.circle.size = self.size

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            new_x = min(max(0, touch.x - self.width / 2), Window.width - self.width)
            new_y = min(max(0, touch.y - self.height / 2), Window.height - self.height)
            self.pos = (new_x, new_y)
            if self.parent:
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

# =====================================================
# Image Processor für Entzerrung
# =====================================================
class ImageProcessor:
    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        pts = np.array(pts)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # TL
        rect[2] = pts[np.argmax(s)]  # BR
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # TR
        rect[3] = pts[np.argmax(diff)]  # BL
        return rect

    def perspective_correct(self, img, corners):
        try:
            rect = self.order_points(corners)
            (tl, tr, br, bl) = rect
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))
            if maxWidth <= 0 or maxHeight <= 0:
                return None
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
            return warped
        except Exception as e:
            print(f"Error in perspective_correct: {e}")
            return None

# =====================================================
# Dashboard
# =====================================================
class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        self.processor = ImageProcessor()

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        self.corners = []
        self.overlay_line = None
        self.entzerrung_enabled = self.store.get("winkel")["value"] if self.store.exists("winkel") else False

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
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1}, spacing=5, padding=5)
        for t, f in [("K", self.show_camera), ("G", self.show_gallery), ("E", self.show_settings),
                     ("A", self.show_a), ("H", self.show_help)]:
            b = Button(text=t, background_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1))
            b.bind(on_press=f)
            self.topbar.add_widget(b)
        self.add_widget(self.topbar)

    # =====================================================
    # Kamera (sichere Auflösung)
    # =====================================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(640, 480))  # kleiner für stabile Start
        self.camera.size_hint = (1, 0.84)
        self.camera.pos_hint = {"x": 0, "y": 0.08}

    # =====================================================
    # Capture Button
    # =====================================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None, None), size=(dp(70), dp(70)),
                              pos_hint={"center_x": 0.5, "y": 0.01}, background_color=(0, 0, 0, 0))
        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.outer_circle = Ellipse(pos=self.capture.pos, size=self.capture.size)
        self.capture.bind(pos=self.update_circle, size=self.update_circle, on_press=self.take_photo)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size

    # =====================================================
    # Kameraanzeige
    # =====================================================
    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        # Android Berechtigung nur prüfen, wenn möglich
        if check_permission and not check_permission(Permission.CAMERA):
            self.add_widget(Label(text="Kamera Berechtigung fehlt", pos_hint={"center_x": .5, "center_y": .5}))
            return

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

        if self.entzerrung_enabled:
            self.init_overlay()

    # =====================================================
    # Overlay für Entzerrung
    # =====================================================
    def init_overlay(self):
        self.corners = []
        for i in range(4):
            c = DraggableCorner()
            self.add_widget(c)
            self.corners.append(c)
        with self.canvas:
            Color(0, 1, 0, 1)
            self.overlay_line = Line(width=2, points=[])
        self.reset_corners()

    def reset_corners(self):
        w, h = Window.width, Window.height
        pad_x = w * 0.15
        pad_y = h * 0.15
        self.corners[0].pos = (pad_x, h - 0.08 * h - pad_y)  # TL
        self.corners[1].pos = (w - pad_x, h - 0.08 * h - pad_y)  # TR
        self.corners[2].pos = (w - pad_x, 0.08 * h + pad_y)  # BR
        self.corners[3].pos = (pad_x, 0.08 * h + pad_y)  # BL
        self.update_lines()

    def update_lines(self):
        if not self.overlay_line:
            return
        points = []
        for idx in [0, 1, 2, 3, 0]:
            c = self.corners[idx]
            points.append(c.center_x)
            points.append(c.center_y)
        self.overlay_line.points = points

    # =====================================================
    # Foto aufnehmen
    # =====================================================
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)

        if self.entzerrung_enabled:
            h_real, w_real = 480, 640  # an die Kameraauflösung anpassen
            mapped_corners = []
            for c in self.corners:
                px = (c.center_x / Window.width) * w_real
                py = h_real - (c.center_y / Window.height) * h_real
                mapped_corners.append([px, py])
            img = cv2.imread(path)
            warped = self.processor.perspective_correct(img, mapped_corners)
            if warped is not None:
                cv2.imwrite(path, warped)

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False
        if not auto:
            self.show_preview(path)

    # =====================================================
    # Vorschau
    # =====================================================
    def show_preview(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation='vertical')
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
            self.add_widget(Label(text="Keine Fotos vorhanden", pos_hint={"center_x": .5, "center_y": .5}))
            return

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=[10, 120, 10, 10], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(280), spacing=5)
            img = Image(source=os.path.join(self.photos_dir, file), allow_stretch=True)
            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)
            name = Label(text=file.replace(".png", ""), size_hint_y=None, height=dp(25))
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
            box.add_widget(Label(text="Norden", color=(1, 0, 0, 1), font_size=20))

        save_btn = Button(text="Speichern")
        save_btn.bind(on_press=lambda x: self.rename_file(filename, name_input.text))
        box.add_widget(save_btn)
        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.delete_file_safe(filename))
        box.add_widget(delete_btn)

        popup = Popup(title=filename.replace(".png", ""), content=box, size_hint=(0.8, 0.7))
        popup.open()

    def delete_file_safe(self, filename):
        try:
            os.remove(os.path.join(self.photos_dir, filename))
        except Exception as e:
            print("Fehler beim Löschen:", e)
        finally:
            self.show_gallery()

    def rename_file(self, old_name, new_name):
        try:
            os.rename(os.path.join(self.photos_dir, old_name),
                      os.path.join(self.photos_dir, f"{new_name}.png"))
        except Exception as e:
            print("Fehler beim Umbenennen:", e)
        self.show_gallery()

    # =====================================================
    # Arduino / Winkel / Hilfe / Einstellungen
    # =====================================================
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        text = "Hier werden später die Arduino Daten angezeigt." if arduino_on else "Daten erst aktivieren"
        self.add_widget(Label(text=text, font_size=24, pos_hint={"center_x": .5, "center_y": .5}))

    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(
            text="Bei Fragen oder Problemen:\nE-Mail Support",
            font_size=20, pos_hint={"center_x": .5, "center_y": .5}))

    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical", padding=[20,120,20,20], spacing=20)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None, height=dp(60)))

        def create_toggle_row(text, key):
            row = BoxLayout(size_hint_y=None, height=dp(60))
            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(80), dp(45)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(80), dp(45)))
            value = self.store.get(key)["value"] if self.store.exists(key) else False

            def update(selected):
                if selected:
                    btn_ja.background_color = (0, 0.6, 0, 1)
                    btn_nein.background_color = (1,1,1,1)
                else:
                    btn_nein.background_color = (0,0.6,0,1)
                    btn_ja.background_color = (1,1,1,1)

            update(value)
            btn_ja.bind(on_press=lambda x: [self.store.put(key, value=True), update(True)])
            btn_nein.bind(on_press=lambda x: [self.store.put(key, value=False), update(False)])
            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row

        layout.add_widget(create_toggle_row("Mit Arduino Daten", "arduino"))
        layout.add_widget(create_toggle_row("Mit Winkel", "winkel"))
        layout.add_widget(create_toggle_row("Automatisch speichern", "auto"))
        self.add_widget(layout)

# =====================================================
# Main App
# =====================================================
if __name__ == "__main__":
    try:
        class MainApp(App):
            def build(self):
                return Dashboard()
        MainApp().run()
    except Exception:
        print("Fehler beim Starten der App:")
        traceback.print_exc()
