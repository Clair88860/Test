from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import mainthread
from kivy.utils import platform

import os

if platform == "android":
    from jnius import autoclass, cast
    from android import activity
    from android.permissions import request_permissions, Permission


class ScannerApp(App):

    def build(self):

        self.layout = BoxLayout(orientation="vertical")

        self.scan_btn = Button(text="Dokument scannen", size_hint=(1, 0.15))
        self.scan_btn.bind(on_press=self.start_scan)

        self.image = Image(size_hint=(1, 0.85))

        self.layout.add_widget(self.image)
        self.layout.add_widget(self.scan_btn)

        if platform == "android":
            request_permissions([Permission.CAMERA])

        return self.layout

    def start_scan(self, instance):

        if platform != "android":
            print("Nur auf Android verfügbar")
            return

        Intent = autoclass("android.content.Intent")
        MediaStore = autoclass("android.provider.MediaStore")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        File = autoclass("java.io.File")
        Uri = autoclass("android.net.Uri")
        FileProvider = autoclass("androidx.core.content.FileProvider")

        currentActivity = PythonActivity.mActivity

        self.image_path = os.path.join(
            currentActivity.getExternalFilesDir(None).getAbsolutePath(),
            "scan.jpg"
        )

        file = File(self.image_path)
        uri = FileProvider.getUriForFile(
            currentActivity,
            currentActivity.getPackageName() + ".provider",
            file
        )

        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        intent.putExtra(MediaStore.EXTRA_OUTPUT, uri)

        activity.bind(on_activity_result=self.on_activity_result)
        currentActivity.startActivityForResult(intent, 1234)

    @mainthread
    def on_activity_result(self, requestCode, resultCode, intent):

        if requestCode == 1234 and resultCode == -1:

            from PIL import Image as PILImage
            img = PILImage.open(self.image_path)
            img = img.rotate(90, expand=True)

            img_data = img.convert("RGB").tobytes()
            texture = Texture.create(size=img.size)
            texture.blit_buffer(img_data, colorfmt="rgb", bufferfmt="ubyte")

            self.image.texture = texture


if __name__ == "__main__":
    ScannerApp().run()
