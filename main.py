from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
import asyncio
import threading
from bleak import BleakClient, BleakScanner

BLE_SERVICE_UUID = "180F"
ANGLE_CHAR_UUID = "2A19"

class AngleApp(App):
    def build(self):
        self.label = Label(text="Warte auf Daten...")
        threading.Thread(target=self.run_ble_thread, daemon=True).start()
        return self.label

    def run_ble_thread(self):
        asyncio.run(self.run_ble())

    async def run_ble(self):
        devices = await BleakScanner.discover()
        target = None
        for d in devices:
            if "Nano33BLE" in d.name:
                target = d
                break
        if not target:
            Clock.schedule_once(lambda dt: setattr(self.label, 'text', "Arduino nicht gefunden!"))
            return

        async with BleakClient(target.address) as client:
            def callback(sender, data):
                angle = int.from_bytes(data, byteorder='little') / 1.0
                # Update UI auf Hauptthread
                Clock.schedule_once(lambda dt: setattr(self.label, 'text', f"Neigung: {angle:.2f}°"))

            await client.start_notify(ANGLE_CHAR_UUID, callback)
            while True:
                await asyncio.sleep(1)

if __name__ == "__main__":
    AngleApp().run()
