from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
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
# Dashboard
# =====================================================
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Kamera
        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.add_widget(self.camera)

        # Eckpunkte
        self.corners = []
        w, h = Window.width, Window.height
        pad_x, pad_y = w * 0.1, h * 0.1
        for pos in [(pad_x, h - pad_y), (w - pad_x, h - pad_y),
                    (w - pad_x, pad_y), (pad_x, pad_y)]:
            c = DraggableCorner(pos=(pos[0]-20, pos[1]-20))
            self.add_widget(c)
            self.corners.append(c)

        # Scan-Button
        self.scan_button = Button(text="Scan", size_hint=(None, None),
                                  size=(150, 60), pos_hint={"center_x": 0.5, "y": 0.02})
        self.scan_button.bind(on_press=self.on_scan)
        self.add_widget(self.scan_button)

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
