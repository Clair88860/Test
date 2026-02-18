[app]

title = DokumentScanner
package.name = dokuscanner
package.domain = org.example
source.include_exts = py,png,jpg,kv,atlas

# Hauptscript
source.dir = .
source.include_patterns = main.py

# Python Requirements
requirements = python3,kivy,opencv-python-headless,numpy

# Android
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.arch = arm64-v8a

# Vollbild
fullscreen = 1

# Orientation
orientation = portrait

[buildozer]

log_level = 2
warn_on_root = 0
