#include <ArduinoBLE.h>

// Eigene UUIDs (wichtig!)
BLEService dataService("12345678-1234-5678-1234-56789abcdef0");
BLEIntCharacteristic dataChar(
  "12345678-1234-5678-1234-56789abcdef1",
  BLERead | BLENotify
);

int angle = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("BLE Fehler!");
    while (1);
  }

  BLE.setLocalName("Arduino_GCS");
  BLE.setAdvertisedService(dataService);

  dataService.addCharacteristic(dataChar);
  BLE.addService(dataService);

  dataChar.writeValue(angle);

  BLE.advertise();
  Serial.println("BLE gestartet");
}

void loop() {

  BLEDevice central = BLE.central();

  if (central) {
    Serial.println("Verbunden");

    while (central.connected()) {

      angle = (angle + 10) % 360;

      dataChar.writeValue(angle);

      Serial.print("Winkel: ");
      Serial.println(angle);

      delay(500);
    }

    Serial.println("Getrennt");
  }
}
