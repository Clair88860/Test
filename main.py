from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import asyncio
import threading
from bleak import BleakClient, BleakScanner
import struct

TARGET_NAME = "Nano33BLE"
ANGLE_CHAR_UUID = "2A19"

class AngleApp(App):
    def build(self):
        self.label = Label(text="Keine Verbindung...")
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.label)
        # Direkt beim Start BLE-Scan starten
        threading.Thread(target=self.connect_arduino, daemon=True).start()
        return layout

    def connect_arduino(self):
        asyncio.run(self.ble_loop())

    async def ble_loop(self):
        while True:
            # Arduino scannen
            devices = await BleakScanner.discover()
            target = None
            for d in devices:
                if TARGET_NAME in d.name:
                    target = d
                    break

            if target:
                try:
                    async with BleakClient(target.address) as client:
                        Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Verbunden mit {TARGET_NAME}"))

                        # Callback für eingehende Daten
                        def callback(sender, data):
                            # Arduino sendet Float als 4-Byte Little Endian
                            angle = struct.unpack('<f', data)[0]
                            Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Neigung: {angle:.2f}°"))

                        await client.start_notify(ANGLE_CHAR_UUID, callback)

                        while client.is_connected:
                            await asyncio.sleep(1)

                except Exception as e:
                    Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Verbindungsfehler: {e}"))

            else:
                Clock.schedule_once(lambda dt: setattr(self.label, 'text', "Arduino nicht gefunden..."))

            await asyncio.sleep(3)  # alle 3 Sekunden erneut scannen

if __name__ == "__main__":
    AngleApp().run()
