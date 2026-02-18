import cv2
import numpy as np
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Ellipse
from kivy.clock import Clock
from kivy.core.camera import Camera as CoreCamera
from kivy.graphics.texture import Texture
from kivy.uix.button import Button
from kivy.utils import platform

if platform == "android":
    from android.permissions import request_permissions, Permission


class ScannerApp(App):

    def build(self):

        if platform == "android":
            request_permissions([Permission.CAMERA])

        self.layout = FloatLayout()

        # Kamera starten
        self.camera = CoreCamera(index=0, resolution=(1280, 720))
        self.camera.start()

        self.image = Image(size_hint=(1, 1))
        self.layout.add_widget(self.image)

        # Overlay Punkte (Startrechteck)
        self.points = [
            [200, 1200],
            [900, 1200],
            [900, 300],
            [200, 300]
        ]

        with self.image.canvas:
            Color(0, 1, 0, 1)
            self.line = Line(width=3)
            self.circles = []
            for p in self.points:
                c = Ellipse(pos=(p[0]-15, p[1]-15), size=(30, 30))
                self.circles.append(c)

        self.update_overlay()

        # Scan Button
        self.capture_btn = Button(
            text="Scannen",
            size_hint=(1, 0.1),
            pos_hint={"x": 0, "y": 0}
        )
        self.capture_btn.bind(on_press=self.capture)
        self.layout.add_widget(self.capture_btn)

        self.image.bind(on_touch_down=self.on_touch_down)
        self.image.bind(on_touch_move=self.on_touch_move)

        Clock.schedule_interval(self.update, 1.0 / 30.0)

        self.drag_index = None

        return self.layout

    # Kamera aktualisieren
    def update(self, dt):

        frame = self.camera.texture
        if not frame:
            return

        buf = frame.pixels
        w, h = frame.size
        img = np.frombuffer(buf, np.uint8).reshape(h, w, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # Hochformat
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self.current_frame = img.copy()

        flipped = cv2.flip(img, 0)
        tex = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='bgr')
        tex.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        self.image.texture = tex

    # Overlay aktualisieren
    def update_overlay(self):
        flat = []
        for p in self.points:
            flat.extend(p)
        self.line.points = flat + flat[:2]

        for i, p in enumerate(self.points):
            self.circles[i].pos = (p[0]-15, p[1]-15)

    # Punkt anklicken
    def on_touch_down(self, instance, touch):
        for i, p in enumerate(self.points):
            if abs(touch.x - p[0]) < 30 and abs(touch.y - p[1]) < 30:
                self.drag_index = i
                return True
        return False

    # Punkt verschieben
    def on_touch_move(self, instance, touch):
        if self.drag_index is not None:
            self.points[self.drag_index] = [touch.x, touch.y]
            self.update_overlay()
            return True
        return False

    # Perspektivische Entzerrung
    def capture(self, instance):

        if not hasattr(self, "current_frame"):
            return

        img = self.current_frame
        img_h, img_w, _ = img.shape

        # Punkte auf Bildgröße mappen
        mapped = []
        for p in self.points:
            x = int((p[0] / self.image.width) * img_w)
            y = int((p[1] / self.image.height) * img_h)
            mapped.append([x, y])

        pts = np.array(mapped, dtype="float32")

        rect = self.order_points(pts)
        warped = self.four_point_transform(img, rect)

        self.line.points = []
        for c in self.circles:
            c.size = (0, 0)

        flipped = cv2.flip(warped, 0)
        tex = Texture.create(size=(warped.shape[1], warped.shape[0]), colorfmt='bgr')
        tex.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        self.image.texture = tex

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def four_point_transform(self, image, rect):
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
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped


if __name__ == "__main__":
    ScannerApp().run()
