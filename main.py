from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import asyncio
import threading
from bleak import BleakClient, BleakScanner

TARGET_NAME = "Arduino_GCS"
ANGLE_CHAR_UUID = "2A57"  # Integer-Characteristic aus deinem Arduino-Code

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
            # Scan nach Arduino
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

                        # Callback für Integer-Daten
                        def callback(sender, data):
                            # data ist ein bytes-Objekt, 4 Bytes für int32
                            angle = int.from_bytes(data, byteorder='little', signed=True)
                            Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Winkel: {angle}°"))

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
