from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics import Color, Line, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
import cv2
import numpy as np
import os

# =====================================================
# Draggable Eckpunkte
# =====================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (50, 50)
        self.background_color = (0, 1, 0, 0.6)

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
# Dashboard
# =====================================================
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Kamera
        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.add_widget(self.camera)

        # Kamera um -90 Grad drehen
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(origin=self.camera.center, angle=-90)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)

        # Eckpunkte
        self.corners = []
        w, h = Window.width, Window.height
        pad_x, pad_y = w * 0.1, h * 0.1
        for pos in [(pad_x, h - pad_y), (w - pad_x, h - pad_y),
                    (w - pad_x, pad_y), (pad_x, pad_y)]:
            c = DraggableCorner(pos=(pos[0]-25, pos[1]-25))
            self.add_widget(c)
            self.corners.append(c)

        # Linien zwischen Punkten
        with self.canvas:
            Color(0, 1, 0, 1)
            self.line = Line(width=2, points=[])
        self.update_lines()

        # Scan-Button
        self.scan_button = Button(text="Scan", size_hint=(None, None),
                                  size=(150, 60), pos_hint={"center_x": 0.5, "y": 0.02})
        self.scan_button.bind(on_press=self.on_scan)
        self.add_widget(self.scan_button)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def update_lines(self):
        points = []
        for idx in [0, 1, 2, 3, 0]:
            c = self.corners[idx]
            points.append(c.center_x)
            points.append(c.center_y)
        self.line.points = points

    def on_scan(self, instance):
        # Foto aufnehmen
        img_path = os.path.join(App.get_running_app().user_data_dir, "scan.png")
        self.camera.export_to_png(img_path)

        # Eckpunkte in Kamera-Bild koordinaten umrechnen
        h_real, w_real = 720, 1280
        mapped = []
        for c in self.corners:
            px = (c.center_x / Window.width) * w_real
            py = h_real - (c.center_y / Window.height) * h_real
            mapped.append([px, py])

        # Perspektivische Korrektur
        img = cv2.imread(img_path)
        warped = self.perspective_correct(img, mapped)
        if warped is not None:
            cv2.imwrite(img_path, warped)

        # Vorschau anzeigen
        self.clear_widgets()
        self.add_widget(Image(source=img_path, allow_stretch=True))

    def perspective_correct(self, img, pts):
        try:
            rect = np.zeros((4, 2), dtype="float32")
            pts = np.array(pts)
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]  # TL
            rect[2] = pts[np.argmax(s)]  # BR
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]  # TR
            rect[3] = pts[np.argmax(diff)]  # BL

            (tl, tr, br, bl) = rect
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))
            if maxWidth <= 0 or maxHeight <= 0:
                return None

            dst = np.array([[0, 0], [maxWidth-1, 0], [maxWidth-1, maxHeight-1], [0, maxHeight-1]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
            return warped
        except Exception as e:
            print("Fehler:", e)
            return None

# =====================================================
# Main App
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
