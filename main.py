import os
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None


# ───────────── DASHBOARD SCREEN ─────────────
class DashboardScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)

        # Sidebar (links, 20%)
        self.sidebar_width = 0.2
        sidebar = BoxLayout(orientation='vertical', size_hint=(self.sidebar_width, 1))
        self.add_widget(sidebar)

        # Hilfe Button
        btn_help = Button(text='?', size_hint=(1, 0.1), background_color=(0.8, 0.8, 0.8, 1))
        btn_help.bind(on_press=self.show_help)
        sidebar.add_widget(btn_help)

        # Kamera Button
        btn_camera = Button(text='K', size_hint=(1, 0.1), background_color=(0.8, 0.8, 0.8, 1))
        btn_camera.bind(on_press=self.show_camera)
        sidebar.add_widget(btn_camera)

        # Galerie Button
        btn_gallery = Button(text='G', size_hint=(1, 0.1), background_color=(0.8, 0.8, 0.8, 1))
        btn_gallery.bind(on_press=self.show_gallery)
        sidebar.add_widget(btn_gallery)

        # Rest als Platzhalter
        sidebar.add_widget(Label(size_hint=(1, 0.7)))

        # Content Bereich (rechts)
        self.content_layout = FloatLayout()
        self.add_widget(self.content_layout)

        # Ordner für Fotos
        self.photos_dir = os.path.join(App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # Standard: Kamera anzeigen
        self.show_camera()

    # ───────────── Kamera anzeigen ─────────────
    def show_camera(self, *args):
        self.content_layout.clear_widgets()

        # Kamera Fläche rechts
        self.camera = Camera(play=True)
        width = Window.width * 0.8
        height = Window.height
        self.camera.size = (width, height)
        self.camera.pos = (0, 0)
        self.content_layout.add_widget(self.camera)

        # Weißer Auslöser rechts mittig
        with self.content_layout.canvas:
            Color(1, 1, 1, 1)
            self.capture_circle = Ellipse(size=(120, 120), pos=(width - 150, height / 2 - 60))

        self.content_layout.bind(on_touch_down=self.take_photo)

    # ───────────── Hilfe anzeigen ─────────────
    def show_help(self, *args):
        self.content_layout.clear_widgets()
        with self.content_layout.canvas:
            Color(0, 0, 0, 0.9)
            Rectangle(size=(Window.width*0.8, Window.height), pos=(0, 0))
        lbl = Label(text="Hier steht die Hilfe", font_size=30, color=(1, 1, 1, 1),
                    pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.content_layout.add_widget(lbl)

    # ───────────── Galerie anzeigen ─────────────
    def show_gallery(self, *args):
        self.content_layout.clear_widgets()

        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=3, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        self.content_layout.add_widget(scroll)

        # Alle Fotos laden
        files = sorted(os.listdir(self.photos_dir), reverse=True)
        for file in files:
            path = os.path.join(self.photos_dir, file)
            if os.path.isfile(path) and path.lower().endswith('.png'):
                img = Image(source=path, size_hint_y=None, height=150)
                img_path = path  # Lokale Variable für Callback

                # Klickbar machen
                img_button = Button(size_hint_y=None, height=150, background_color=(0,0,0,0))
                img_button.add_widget(img)
                img_button.bind(on_press=lambda instance, p=img_path: self.show_preview(p))
                grid.add_widget(img_button)

    # ───────────── Foto aufnehmen ─────────────
    def take_photo(self, instance, touch):
        x, y = self.capture_circle.pos
        w, h = self.capture_circle.size
        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            filename = os.path.join(self.photos_dir, f"photo_{int(time.time())}.png")
            self.camera.export_to_png(filename)
            App.get_running_app().last_photo = filename
            # Direkt zur Vorschau
            self.show_preview(filename)

    # ───────────── Vorschau anzeigen ─────────────
    def show_preview(self, photo_path):
        self.content_layout.clear_widgets()

        layout = FloatLayout()
        self.content_layout.add_widget(layout)

        if os.path.exists(photo_path):
            image = Image(source=photo_path, size_hint=(1,1), allow_stretch=True, keep_ratio=True)
            layout.add_widget(image)

        # Wiederholen Button
        btn_retry = Button(text="Wiederholen", size_hint=(0.3,0.15),
                           pos_hint={"x":0.1,"y":0.05}, background_color=(0.2,0.2,0.2,1))
        btn_retry.bind(on_press=lambda x: self.show_camera())
        layout.add_widget(btn_retry)

        # Fertig Button
        btn_done = Button(text="Fertig", size_hint=(0.3,0.15),
                          pos_hint={"x":0.6,"y":0.05}, background_color=(0.2,0.2,0.2,1))
        btn_done.bind(on_press=lambda x: self.save_photo(photo_path))
        layout.add_widget(btn_done)

    # ───────────── Foto speichern ─────────────
    def save_photo(self, photo_path):
        content = FloatLayout()
        textinput = TextInput(hint_text="Dateiname eingeben", size_hint=(0.8,0.2),
                              pos_hint={"x":0.1,"y":0.5})
        btn_save = Button(text="Speichern", size_hint=(0.5,0.2), pos_hint={"x":0.25,"y":0.2})
        content.add_widget(textinput)
        content.add_widget(btn_save)
        popup = Popup(title="Foto speichern", content=content, size_hint=(0.8,0.5))

        def save_file(instance_btn):
            filename = textinput.text.strip()
            if filename:
                save_dir = os.path.join(App.get_running_app().user_data_dir, "documents")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, f"{filename}.png")
                with open(photo_path, "rb") as f_src, open(save_path, "wb") as f_dst:
                    f_dst.write(f_src.read())
                popup.dismiss()
        btn_save.bind(on_press=save_file)
        popup.open()


# ───────────── MAIN APP ─────────────
class MainApp(App):
    last_photo = None

    def build(self):
        return DashboardScreen()


if __name__ == "__main__":
    MainApp().run()
