import os
import time
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.uix.camera import Camera
from kivy.utils import platform


class MainApp(App):

    def build(self):
        # Hauptlayout: vertikal
        self.root = BoxLayout(orientation="vertical")

        # Dashboard oben – immer sichtbar
        self.topbar = Label(
            text="Winkel: --° | Richtung: --",
            size_hint_y=0.1,
            font_size=22
        )
        self.root.add_widget(self.topbar)

        # Content Bereich (dynamisch)
        self.content = BoxLayout()
        self.root.add_widget(self.content)

        self.arduino_enabled = False

        # Startseite = Kamera
        self.show_camera()
        return self.root

    # ====================== KAMERA ===========================
    def show_camera(self):
        self.content.clear_widgets()

        layout = BoxLayout(orientation="vertical")
        self.camera = Camera(play=True)
        layout.add_widget(self.camera)

        btn = Button(text="Foto aufnehmen", size_hint_y=0.15)
        btn.bind(on_press=self.capture)
        layout.add_widget(btn)

        self.content.add_widget(layout)

    def capture(self, instance):
        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])
        number = len(files) + 1
        filename = f"{number:04d}.png"
        path = os.path.join(self.user_data_dir, filename)
        self.camera.export_to_png(path)
        self.show_preview(path)

    def show_preview(self, path):
        self.content.clear_widgets()

        layout = BoxLayout(orientation="vertical")
        img = Image(source=path)
        layout.add_widget(img)

        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")

        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())

        btns.add_widget(save)
        btns.add_widget(repeat)
        layout.add_widget(btns)
        self.content.add_widget(layout)

    # ====================== GALERIE ==========================
    def show_gallery(self):
        self.content.clear_widgets()
        scroll = ScrollView()
        grid = BoxLayout(orientation="vertical", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted([f for f in os.listdir(self.user_data_dir) if f.endswith(".png")])

        for f in files:
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=500)
            lbl = Label(text=f)
            img = Image(source=os.path.join(self.user_data_dir, f))
            img.bind(on_touch_down=lambda inst, touch, file=f:
                     self.open_single_view(file) if inst.collide_point(*touch.pos) else None)
            box.add_widget(lbl)
            box.add_widget(img)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.content.add_widget(scroll)

    # ================= EINZELANSICHT =========================
    def open_single_view(self, filename):
        self.content.clear_widgets()
        path = os.path.join(self.user_data_dir, filename)
        layout = BoxLayout(orientation="vertical")

        float_layout = FloatLayout()
        img = Image(source=path)
        float_layout.add_widget(img)

        if self.arduino_enabled:
            overlay = Label(
                text="Norden",
                color=(1,1,1,1),
                size_hint=(None,None),
                pos_hint={"right":1,"top":1}
            )
            float_layout.add_widget(overlay)

        layout.add_widget(float_layout)

        # Name + i Button
        name_row = BoxLayout(size_hint_y=0.15)
        name_label = Label(text=filename.replace(".png",""))
        info_btn = Button(text="i", size_hint_x=0.2)
        info_btn.bind(on_press=lambda x: self.open_info_popup(filename))
        name_row.add_widget(name_label)
        name_row.add_widget(info_btn)

        layout.add_widget(name_row)
        self.content.add_widget(layout)

    # ================= INFO POPUP =========================
    def open_info_popup(self, filename):
        path = os.path.join(self.user_data_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(Label(text="Name (bearbeiten):"))
        box.add_widget(name_input)

        timestamp = os.path.getmtime(path)
        date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")
        box.add_widget(Label(text=f"Datum: {date}"))

        def confirm_delete(instance):
            confirm_box = BoxLayout(orientation="vertical")
            confirm_box.add_widget(Label(text="Wirklich löschen?"))
            yes = Button(text="Ja")
            no = Button(text="Nein")
            def delete_now(x):
                os.remove(path)
                confirm_popup.dismiss()
                popup.dismiss()
                self.show_gallery()
            yes.bind(on_press=delete_now)
            no.bind(on_press=lambda x: confirm_popup.dismiss())
            confirm_box.add_widget(yes)
            confirm_box.add_widget(no)
            confirm_popup = Popup(title="Sicherheitsabfrage",
                                  content=confirm_box,
                                  size_hint=(0.7,0.4))
            confirm_popup.open()

        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=confirm_delete)
        box.add_widget(delete_btn)

        save_btn = Button(text="Speichern")
        save_btn.bind(on_press=lambda x: self.save_name(filename, name_input.text))
        box.add_widget(save_btn)

        popup = Popup(title="Info", content=box, size_hint=(0.8,0.8))
        popup.open()

    def save_name(self, old_name, new_name):
        old_path = os.path.join(self.user_data_dir, old_name)
        new_path = os.path.join(self.user_data_dir, new_name + ".png")
        os.rename(old_path, new_path)
        self.show_gallery()

    # =================== E SEITE ==========================
    def show_e(self):
        self.content.clear_widgets()
        layout = BoxLayout(orientation="vertical", spacing=20, padding=20)
        row = BoxLayout()
        row.add_widget(Label(text="Mit Arduino"))
        ja = ToggleButton(text="Ja", group="arduino")
        nein = ToggleButton(text="Nein", group="arduino", state="down")
        def toggle(btn):
            self.arduino_enabled = (btn.text=="Ja" and btn.state=="down")
        ja.bind(on_press=toggle)
        nein.bind(on_press=toggle)
        row.add_widget(ja)
        row.add_widget(nein)
        layout.add_widget(row)
        self.content.add_widget(layout)


if __name__ == "__main__":
    MainApp().run()
