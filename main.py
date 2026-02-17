from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import asyncio
import threading
from bleak import BleakClient, BleakScanner
import struct

# Name des Arduino BLE-Geräts
TARGET_NAME = "Nano33BLE"
# UUID der Characteristic, die den Neigungswinkel sendet
ANGLE_CHAR_UUID = "2A19"

class AngleApp(App):
    def build(self):
        # Layout
        self.label = Label(text="Keine Verbindung...")
        self.connect_button = Button(text="Verbinde mit Arduino")
        self.connect_button.bind(on_press=lambda x: threading.Thread(target=self.connect_arduino, daemon=True).start())

        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.label)
        layout.add_widget(self.connect_button)
        return layout

    def connect_arduino(self):
        # BLE-Loop in eigenem Thread starten
        asyncio.run(self.ble_loop())

    async def ble_loop(self):
        while True:
            # 1️⃣ Scan nach Arduino
            devices = await BleakScanner.discover()
            target = None
            for d in devices:
                if TARGET_NAME in d.name:
                    target = d
                    break

            if target:
                try:
                    async with BleakClient(target.address) as client:
                        # Update UI auf Hauptthread
                        Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Verbunden mit {TARGET_NAME}"))

                        # Callback für Winkel-Daten
                        def callback(sender, data):
                            # Arduino sendet Float als 4 Byte Little Endian
                            angle = struct.unpack('<f', data)[0]
                            Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Neigung: {angle:.2f}°"))

                        await client.start_notify(ANGLE_CHAR_UUID, callback)

                        # Solange verbunden, sleep
                        while client.is_connected:
                            await asyncio.sleep(1)

                except Exception as e:
                    Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Verbindungsfehler: {e}"))

            else:
                # Arduino nicht gefunden
                Clock.schedule_once(lambda dt: setattr(self.label, 'text', "Arduino nicht gefunden..."))

            # Alle 3 Sekunden erneut scannen
            await asyncio.sleep(3)

if __name__ == "__main__":
    AngleApp().run()
