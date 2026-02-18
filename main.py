import os
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.graphics import Color, Ellipse, Line, Rotate, PushMatrix, PopMatrix
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore

import cv2
import numpy as np

try:
    from android.permissions import request_permissions, Permission
except:
    request_permissions = None
    Permission = None

# =========================
# Draggable Eckpunkte
# =========================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (40, 40)
        with self.canvas.before:
            Color(0, 1, 0, 0.7)
            self.circle = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.update_circle, size=self.update_circle)

    def update_circle(self, *args):
        self.circle.pos = self.pos
        self.circle.size = self.size

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            x = min(max(0, touch.x - self.width / 2), Window.width - self.width)
            y = min(max(0, touch.y - self.height / 2), Window.height - self.height)
            self.pos = (x, y)
            if self.parent:
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

# =========================
# Image Processor
# =========================
class ImageProcessor:
    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        pts = np.array(pts)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def perspective_correct(self, img, corners):
        rect = self.order_points(corners)
        (tl, tr, br, bl) = rect
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
        return warped

# =========================
# Dashboard
# =========================
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Permissions für Android
        if request_permissions:
            request_permissions([Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE])

        self.processor = ImageProcessor()
        self.user_dir = App.get_running_app().user_data_dir
        self.photos_dir = os.path.join(self.user_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.build_camera()
        self.build_capture_button()

        # Eckpunkte Overlay
        self.corners = []
        self.overlay_line = None
        Clock.schedule_once(lambda dt: self.init_overlay(), 0.2)

    # =========================
    # Kamera
    # =========================
    def build_camera(self):
        self.camera = Camera(play=True, resolution=(1920, 1080))
        self.camera.size_hint = (1, 1)
        self.camera.pos_hint = {"x": 0, "y": 0}
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)
        self.add_widget(self.camera)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # =========================
    # Capture Button
    # =========================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None, None), size=(dp(70), dp(70)),
                              pos_hint={"center_x": 0.5, "y": 0.02}, background_color=(0,0,0,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.outer = Ellipse(pos=self.capture.pos, size=self.capture.size)
        self.capture.bind(pos=self.update_outer, size=self.update_outer, on_press=self.take_photo)
        self.add_widget(self.capture)

    def update_outer(self, *args):
        self.outer.pos = self.capture.pos
        self.outer.size = self.capture.size

    # =========================
    # Overlay Eckpunkte
    # =========================
    def init_overlay(self):
        for i in range(4):
            c = DraggableCorner()
            self.add_widget(c)
            self.corners.append(c)
        self.overlay_line = Line(width=2, points=[])
        with self.canvas:
            Color(0,1,0,1)
            self.canvas.add(self.overlay_line)
        self.reset_corners()

    def reset_corners(self):
        w, h = Window.width, Window.height
        pad_x, pad_y = w*0.1, h*0.1
        self.corners[0].pos = (pad_x, h - pad_y - 40)
        self.corners[1].pos = (w - pad_x - 40, h - pad_y - 40)
        self.corners[2].pos = (w - pad_x - 40, pad_y)
        self.corners[3].pos = (pad_x, pad_y)
        self.update_lines()

    def update_lines(self):
        if not self.overlay_line:
            return
        pts = []
        for idx in [0,1,2,3,0]:
            c = self.corners[idx]
            pts += [c.center_x, c.center_y]
        self.overlay_line.points = pts

    # =========================
    # Foto aufnehmen
    # =========================
    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "scan.png")
        self.camera.export_to_png(temp_path)

        # Eckpunkte für Entzerrung
        mapped = []
        for c in self.corners:
            px = (c.center_x / Window.width) * 1080
            py = 1920 - (c.center_y / Window.height) * 1920
            mapped.append([px, py])

        img = cv2.imread(temp_path)
        warped = self.processor.perspective_correct(img, mapped)
        if warped is not None:
            cv2.imwrite(temp_path, warped)

        self.show_preview(temp_path)

    # =========================
    # Vorschau
    # =========================
    def show_preview(self, path):
        self.clear_widgets()
        img = Image(source=path, allow_stretch=True)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(img)
        btn = Button(text="Neues Scan", size_hint_y=0.15)
        btn.bind(on_press=lambda x: App.get_running_app().stop())
        layout.add_widget(btn)
        self.add_widget(layout)

# =========================
# Main
# =========================
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
