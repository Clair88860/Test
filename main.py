import cv2
import numpy as np
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.graphics import Color, Line
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

        # Kamera
        self.camera = CoreCamera(index=0, resolution=(1280, 720))
        self.camera.start()

        self.image = Image(size_hint=(1, 1))
        self.layout.add_widget(self.image)

        # Overlay
        with self.image.canvas:
            Color(0, 1, 0, 1)
            self.line = Line(width=3)

        # Button
        self.capture_btn = Button(
            text="Scannen",
            size_hint=(1, 0.1),
            pos_hint={"x": 0, "y": 0}
        )
        self.capture_btn.bind(on_press=self.capture)
        self.layout.add_widget(self.capture_btn)

        Clock.schedule_interval(self.update, 1.0 / 30.0)

        return self.layout

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def four_point_transform(self, image, pts):
        rect = self.order_points(pts)
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

    def update(self, dt):

        frame = self.camera.texture
        if not frame:
            return

        buf = frame.pixels
        w, h = frame.size
        img = np.frombuffer(buf, np.uint8).reshape(h, w, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # Hochformat drehen
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self.current_frame = img.copy()

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 75, 200)

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        self.doc_cnt = None

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                self.doc_cnt = approx
                break

        if self.doc_cnt is not None:
            pts = self.doc_cnt.reshape(4, 2)

            # Overlay zeichnen
            scaled = []
            img_h, img_w, _ = img.shape
            widget_w = self.image.width
            widget_h = self.image.height

            for p in pts:
                x = (p[0] / img_w) * widget_w
                y = (p[1] / img_h) * widget_h
                scaled.extend([x, widget_h - y])

            self.line.points = scaled + scaled[:2]

        # Bild anzeigen
        flipped = cv2.flip(img, 0)
        tex = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='bgr')
        tex.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        self.image.texture = tex

    def capture(self, instance):

        if self.doc_cnt is None:
            return

        warped = self.four_point_transform(self.current_frame,
                                            self.doc_cnt.reshape(4, 2))

        cv2.imwrite("scan.jpg", warped)

        # Ergebnis anzeigen
        self.line.points = []
        tex = Texture.create(size=(warped.shape[1], warped.shape[0]), colorfmt='bgr')
        flipped = cv2.flip(warped, 0)
        tex.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        self.image.texture = tex


if __name__ == "__main__":
    ScannerApp().run()
