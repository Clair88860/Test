[app]

# Name der App (wird auf dem Handy angezeigt)
title = Archäologie

# Paketname (muss klein sein, keine Umlaute!)
package.name = archaeologie

# Domain (frei wählbar)
package.domain = org.example

# Quellcode
source.dir = .
source.include_exts = py

# Version
version = 1.0

# Einstiegspunkt
entrypoint = main.py

# Benötigte Bibliotheken
orientation = portrait
requirements = python3,kivy,pyjnius,android,pillow

android.permissions = CAMERA,BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION,BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_COARSE_LOCATION, BLUETOOTH, BLUETOOTH_ADMIN
      

# Anzeige
fullscreen = 0


# Android SDK / NDK
android.api = 33
android.minapi = 26
android.sdk = 33
android.ndk = 25


# Architektur
android.archs = arm64-v8a

# Debug (optional)
android.logcat_filters = *:S python:D

# Buildozer
warn_on_root = 1
