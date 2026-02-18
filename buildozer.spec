[app]
title = DocScanner
package.name = docscanner
package.domain = org.example
source.include_exts = py,png,jpg
version = 1.0.0
orientation = portrait
requirements = python3,kivy==2.1.0,opencv-python-headless,numpy
android.api = 33
android.ndk = 25b
android.minapi = 21
source.dir = .
android.arch = arm64-v8a
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
