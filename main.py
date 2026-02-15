import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.metrics import dp

Window.clearcolor = (0.1, 0.1, 0.12, 1)


class TopButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = (0.2, 0.2, 0.25, 1)
        self.color = (1, 1, 1, 1)


class Dashboard(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.photos_dir = os.path.join(
            App.get_running_app().user_data_dir,
            "photos"
        )
        os.makedirs(self.photos_dir, exist_ok=True)

        # ==================================================
        # TOP NAVIGATION
        # ==================================================
        topbar = BoxLayout(
            size_hint=(1, 0.1),
            spacing=dp(10),
            padding=dp(10)
        )

        for text, func in [
            ("?", self.show_help),
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_extra)
        ]:
            btn = TopButton(text=text)
            btn.bind(on_press=func)
            topbar.add_widget(btn)

        self.add_widget(topbar)

        # ==================================================
        # CONTENT
        # ==================================================
        self.content = FloatLayout()
        self.add_widget(self.content)

        # ==================================================
        # BOTTOM CAMERA BUTTON
        # ==================================================
        self.bottom_bar = FloatLayout(size_hint=(1, 0.15))
        self.capture_button = Button(
            text="",
            size_hint=(None, None),
            size=(dp(90), dp(90)),
            background_normal="",
            background_color=(1, 1, 1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.capture_button.bind(on_press=self.take_photo)
        self.bottom_bar.add_widget(self.capture_button)

        self.add_widget(self.bottom_bar)

        Window.bind(on_resize=self.update_orientation)

        self.show_camera()

    # ==================================================
    # CAMERA
    # ==================================================
    def show_camera(self, *args):
        self.content.clear_widgets()
        self.bottom_bar.opacity = 1

        self.camera = Camera(play=True, resolution=(1280, 720))
        self.camera.size_hint = (1, 1)
        self.content.add_widget(self.camera)

        self.update_orientation()

    def update_orientation(self, *args):
        if hasattr(self, "camera"):
            if Window.height > Window.width:
                self.camera.rotation = 90
            else:
                self.camera.rotation = 0

    def take_photo(self, instance):
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)

    # ==================================================
    # HELP
    # ==================================================
    def show_help(self, *args):
        self.content.clear_widgets()
        self.bottom_bar.opacity = 0

        self.content.add_widget(Label(
            text="Hilfe",
            font_size=40,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # GALLERY
    # ==================================================
    def show_gallery(self, *args):
        self.content.clear_widgets()
        self.bottom_bar.opacity = 0

        self.content.add_widget(Label(
            text="Galerie folgt noch",
            font_size=30,
            pos_hint={"center_x": 0.5,
                      "center_y": 0.5}
        ))

    # ==================================================
    # EXTRA (E)
    # ==================================================
    def show_extra(self, *args):
        self.content.clear_widgets()
        self.bottom_bar.opacity = 0

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(40),
            spacing=dp(30)
        )

        # 1. Daten von Arduino
        layout.add_widget(self.create_toggle_row("Daten von Arduino"))

        # 2. mit Winkel
        layout.add_widget(self.create_toggle_row("mit Winkel"))

        self.content.add_widget(layout)

    def create_toggle_row(self, text):

        row = BoxLayout(spacing=dp(20))

        label = Label(text=text,
                      size_hint=(0.5, 1),
                      halign="left",
                      valign="middle")
        label.bind(size=label.setter('text_size'))

        btn_yes = Button(text="Ja",
                         background_normal="",
                         background_color=(0.3, 0.3, 0.3, 1))

        btn_no = Button(text="Nein",
                        background_normal="",
                        background_color=(0.3, 0.3, 0.3, 1))

        def select_yes(instance):
            btn_yes.background_color = (0, 0.7, 0, 1)
            btn_no.background_color = (0.3, 0.3, 0.3, 1)

        def select_no(instance):
            btn_no.background_color = (0, 0.7, 0, 1)
            btn_yes.background_color = (0.3, 0.3, 0.3, 1)

        btn_yes.bind(on_press=select_yes)
        btn_no.bind(on_press=select_no)

        row.add_widget(label)
        row.add_widget(btn_yes)
        row.add_widget(btn_no)

        return row


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
