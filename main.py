import os
import cv2
import numpy as np
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label

# =====================================================
# Draggable Eckpunkte
# =====================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (40, 40)
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
# Image Processor
# =====================================================
class ImageProcessor:
    @staticmethod
    def order_points(pts):
        rect = np.zeros((4, 2), dtype="float32")
        pts = np.array(pts)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    @staticmethod
    def perspective_correct(img, corners):
        try:
            rect = ImageProcessor.order_points(corners)
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
        except Exception as e:
            print(f"Error in perspective_correct: {e}")
            return img

# =====================================================
# Dashboard / Haupt-App
# =====================================================
class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processor = ImageProcessor()
        self.corners = []
        self.capture_button = None
        self.scanned_img_widget = None

        # OpenCV VideoCapture
        self.capture = cv2.VideoCapture(0)  # Kamera 0
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Texture Widget für Kamera
        self.cam_widget = Image(size_hint=(1, 1), pos=(0, 0))
        self.add_widget(self.cam_widget)

        # Eckpunkte Overlay
        self.init_corners()

        # Scan Button
        self.capture_button = Button(text="Scan", size_hint=(None, None),
                                     size=(150, 60), pos_hint={"center_x": 0.5, "y": 0.02})
        self.capture_button.bind(on_press=self.scan_document)
        self.add_widget(self.capture_button)

        Clock.schedule_interval(self.update_frame, 1.0 / 30)

    # =====================================================
    # Eckpunkte erzeugen
    # =====================================================
    def init_corners(self):
        w, h = Window.width, Window.height
        pad_x, pad_y = w * 0.1, h * 0.1
        for pos in [(pad_x, h - pad_y), (w - pad_x, h - pad_y),
                    (w - pad_x, pad_y), (pad_x, pad_y)]:
            c = DraggableCorner(pos=(pos[0] - 20, pos[1] - 20))
            self.add_widget(c)
            self.corners.append(c)

    # =====================================================
    # Linien zwischen Eckpunkten aktualisieren
    # =====================================================
    def update_lines(self):
        # Optional: Linien zwischen Punkten zeichnen
        pass  # Für einfache Version lassen wir es weg

    # =====================================================
    # Frame von Kamera lesen
    # =====================================================
    def update_frame(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return
        # Hochformat
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        frame = cv2.flip(frame, 1)  # Spiegelung

        # OpenCV -> Kivy Texture
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.cam_widget.texture = texture
        self.cam_widget.canvas.ask_update()
        self.current_frame = frame

    # =====================================================
    # Scan Button
    # =====================================================
    def scan_document(self, instance):
        if not hasattr(self, "current_frame"):
            return
        corners = []
        for c in self.corners:
            x = (c.center_x / Window.width) * self.current_frame.shape[1]
            y = (c.center_y / Window.height) * self.current_frame.shape[0]
            corners.append([x, y])
        warped = self.processor.perspective_correct(self.current_frame, corners)
        # Anzeigen
        self.show_scanned(warped)

    # =====================================================
    # Gescanntes Bild anzeigen
    # =====================================================
    def show_scanned(self, img):
        self.clear_widgets()
        # Image Widget
        buf = cv2.flip(img, 0).tobytes()
        texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.scanned_img_widget = Image(texture=texture, size_hint=(1, 1))
        self.add_widget(self.scanned_img_widget)

# =====================================================
# Main App
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
