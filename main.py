import os
import cv2
import numpy as np
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture

class DocumentScanner(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Bild-Widget zum Anzeigen des gescannten Dokuments
        self.img_widget = Image(size_hint=(1, 1))
        self.add_widget(self.img_widget)

        # Scan Button
        self.scan_btn = Button(text="Scan Dokument",
                               size_hint=(0.5, 0.1),
                               pos_hint={"center_x": 0.5, "y": 0.05})
        self.scan_btn.bind(on_press=self.scan_document)
        self.add_widget(self.scan_btn)

    def scan_document(self, instance):
        # Kamera öffnen und Foto aufnehmen
        cap = cv2.VideoCapture(0)  # 0 = Rückkamera auf vielen Geräten
        if not cap.isOpened():
            print("Kamera konnte nicht geöffnet werden")
            return

        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("Kein Bild aufgenommen")
            return

        # Hochformat erzwingen
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        # Dokument erkennen und entzerren
        scanned = self.detect_document(frame)
        if scanned is None:
            scanned = frame

        # Bild in Kivy anzeigen
        self.display_image(scanned)

    def detect_document(self, img):
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 75, 200)

            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            for cnt in contours:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2)
                    return self.four_point_transform(img, pts)

            return None
        except Exception as e:
            print("Fehler bei Dokumenterkennung:", e)
            return None

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
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped

    def display_image(self, img):
        buf = cv2.flip(img, 0).tobytes()
        texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_widget.texture = texture

class MainApp(App):
    def build(self):
        return DocumentScanner()

if __name__ == "__main__":
    MainApp().run()
