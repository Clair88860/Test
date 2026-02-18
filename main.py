import cv2
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window

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
            return True
        return super().on_touch_move(touch)

# =====================================================
# Haupt-Widget
# =====================================================
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Kamera OpenCV
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Kameraanzeige
        self.cam_widget = Image(size_hint=(1, 1))
        self.add_widget(self.cam_widget)

        # Eckpunkte erzeugen
        self.corners = []
        self.init_corners()

        # Scan-Button (noch ohne Verarbeitung)
        self.scan_button = Button(text="Scan", size_hint=(None, None),
                                  size=(150, 60), pos_hint={"center_x": 0.5, "y": 0.02})
        self.scan_button.bind(on_press=self.on_scan)
        self.add_widget(self.scan_button)

        Clock.schedule_interval(self.update_frame, 1/30)

    def init_corners(self):
        w, h = Window.width, Window.height
        pad_x, pad_y = w * 0.1, h * 0.1
        for pos in [(pad_x, h - pad_y), (w - pad_x, h - pad_y),
                    (w - pad_x, pad_y), (pad_x, pad_y)]:
            c = DraggableCorner(pos=(pos[0]-20, pos[1]-20))
            self.add_widget(c)
            self.corners.append(c)

    def update_frame(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return
        # Hochformat
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        frame = cv2.flip(frame, 1)
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.cam_widget.texture = texture
        self.cam_widget.canvas.ask_update()
        self.current_frame = frame

    def on_scan(self, instance):
        # Minimal: nur Info ausgeben
        print("Scan gedrückt – noch keine Verarbeitung")

# =====================================================
# Main App
# =====================================================
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__ == "__main__":
    MainApp().run()
