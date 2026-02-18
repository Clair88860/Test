import os
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.camera import Camera
from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

import cv2
import numpy as np

# ------------------------
# Draggable Eckpunkte
# ------------------------
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
            new_x = min(max(0, touch.x - self.width/2), Window.width - self.width)
            new_y = min(max(0, touch.y - self.height/2), Window.height - self.height)
            self.pos = (new_x, new_y)
            if self.parent:
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

# ------------------------
# Image Processor
# ------------------------
class ImageProcessor:
    def order_points(self, pts):
        rect = np.zeros((4,2), dtype="float32")
        pts = np.array(pts)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # TL
        rect[2] = pts[np.argmax(s)]  # BR
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # TR
        rect[3] = pts[np.argmax(diff)]  # BL
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
        if maxWidth <= 0 or maxHeight <= 0:
            return None
        dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
        return warped

# ------------------------
# Dashboard
# ------------------------
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.processor = ImageProcessor()

        self.build_camera()
        self.corners = []
        self.overlay_line = None
        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920,1080))
        self.camera.size_hint = (1, 1)
        self.camera.pos_hint = {"x":0, "y":0}

    def show_camera(self):
        self.clear_widgets()
        self.add_widget(self.camera)
        self.camera.play = True

        # Eckpunkte erstellen
        self.init_overlay()

        # Scan Button
        scan_btn = Button(text="Scannen", size_hint=(None,None), size=(dp(120),dp(50)),
                          pos_hint={"center_x":0.5, "y":0.02})
        scan_btn.bind(on_press=self.scan_document)
        self.add_widget(scan_btn)

    def init_overlay(self):
        self.corners = []
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
        pad_x = w*0.15
        pad_y = h*0.15
        self.corners[0].pos = (pad_x, h - pad_y - 40)  # TL
        self.corners[1].pos = (w - pad_x - 40, h - pad_y - 40)  # TR
        self.corners[2].pos = (w - pad_x - 40, pad_y)  # BR
        self.corners[3].pos = (pad_x, pad_y)  # BL
        self.update_lines()

    def update_lines(self):
        points = []
        for idx in [0,1,2,3,0]:
            c = self.corners[idx]
            points.append(c.center_x)
            points.append(c.center_y)
        self.overlay_line.points = points

    def scan_document(self, instance):
        # Bild aufnehmen
        path = "scanned.png"
        self.camera.export_to_png(path)

        # Eckpunkte mappen
        h_real, w_real = 1080, 1920
        mapped_corners = []
        for c in self.corners:
            px = (c.center_x / Window.width) * w_real
            py = h_real - (c.center_y / Window.height) * h_real
            mapped_corners.append([px, py])

        img = cv2.imread(path)
        warped = self.processor.perspective_correct(img, mapped_corners)
        if warped is not None:
            cv2.imwrite(path, warped)

        # Bild anzeigen
        self.clear_widgets()
        self.add_widget(Image(source=path, allow_stretch=True))

# ------------------------
# App
# ------------------------
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
