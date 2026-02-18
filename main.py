from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.camera import Camera
from kivy.graphics import Color, Line, PushMatrix, PopMatrix, Rotate
from kivy.core.window import Window
from kivy.clock import Clock
import cv2
import numpy as np
import os


# =====================================================
# Verschiebbare Punkte (weicher Drag)
# =====================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (60, 60)
        self.background_color = (0, 1, 0, 0.7)
        self.dragging = False

    def on_touch_down(self, touch):
        # größerer Fangbereich
        if abs(touch.x - self.center_x) < 80 and abs(touch.y - self.center_y) < 80:
            self.dragging = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.dragging:
            x = min(max(0, touch.x - self.width/2), Window.width - self.width)
            y = min(max(0, touch.y - self.height/2), Window.height - self.height)
            self.pos = (x, y)
            if self.parent:
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.dragging = False
        return super().on_touch_up(touch)


# =====================================================
# Hauptlayout
# =====================================================
class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # -------------------
        # Kamera Fullscreen
        # -------------------
        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.camera.pos_hint = {"x": 0, "y": 0}
        self.add_widget(self.camera)

        # Kamera drehen
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(size=self.update_rotation, pos=self.update_rotation)

        # -------------------
        # Overlay Punkte
        # -------------------
        self.corners = []
        Clock.schedule_once(self.init_overlay, 0.5)

        # -------------------
        # Scan Button
        # -------------------
        self.scan_btn = Button(text="SCAN",
                               size_hint=(None, None),
                               size=(200, 70),
                               pos_hint={"center_x": 0.5, "y": 0.02})
        self.scan_btn.bind(on_press=self.scan_document)
        self.add_widget(self.scan_btn)

    # =====================================================
    # Kamera Rotation Update
    # =====================================================
    def update_rotation(self, *args):
        self.rot.origin = self.camera.center

    # =====================================================
    # Overlay Initialisieren
    # =====================================================
    def init_overlay(self, dt):

        w, h = Window.width, Window.height
        pad_x, pad_y = w * 0.15, h * 0.2

        positions = [
            (pad_x, h - pad_y),
            (w - pad_x, h - pad_y),
            (w - pad_x, pad_y),
            (pad_x, pad_y)
        ]

        for pos in positions:
            c = DraggableCorner(pos=(pos[0] - 30, pos[1] - 30))
            self.add_widget(c)
            self.corners.append(c)

        with self.canvas:
            Color(0, 1, 0, 1)
            self.line = Line(width=3)

        self.update_lines()

    # =====================================================
    # Linien aktualisieren
    # =====================================================
    def update_lines(self):
        pts = []
        for i in [0, 1, 2, 3, 0]:
            pts.append(self.corners[i].center_x)
            pts.append(self.corners[i].center_y)
        self.line.points = pts

    # =====================================================
    # Scan Funktion
    # =====================================================
    def scan_document(self, instance):

        img_path = os.path.join(App.get_running_app().user_data_dir, "scan.png")
        self.camera.export_to_png(img_path)

        img = cv2.imread(img_path)
        if img is None:
            return

        h_real, w_real = img.shape[:2]

        mapped = []
        for c in self.corners:
            x = (c.center_x / Window.width) * w_real
            y = h_real - (c.center_y / Window.height) * h_real
            mapped.append([x, y])

        warped = self.perspective_transform(img, mapped)

        if warped is None:
            return

        cv2.imwrite(img_path, warped)

        # Ergebnis anzeigen
        self.clear_widgets()
        result = Image(source=img_path, allow_stretch=True)
        self.add_widget(result)

    # =====================================================
    # Perspektivische Transformation
    # =====================================================
    def perspective_transform(self, img, pts):

        pts = np.array(pts, dtype="float32")

        s = pts.sum(axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = int(max(widthA, widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = int(max(heightA, heightB))

        if maxWidth <= 0 or maxHeight <= 0:
            return None

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))

        return warped


# =====================================================
# App Start
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
