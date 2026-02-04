#include <stdio.h>

// Bluetooth Classic
#include "BluetoothSerial.h"

// WiFi only used to query MAC address, no network connection needed
#include <WiFi.h>

// Sensor Libraries
#include <Adafruit_SCD30.h>

// ------------------------------------------------------------------
// Globals
// ------------------------------------------------------------------

BluetoothSerial SerialBT;
Adafruit_SCD30 scd30 = Adafruit_SCD30();

// Helper: get MAC address as string "AA:BB:CC:DD:EE:FF"
String getMacString() {
  // WiFi library’s MAC string is fine for identification
  String mac = WiFi.macAddress(); // e.g. "24:6F:28:AA:BB:CC"
  mac.toUpperCase();
  return mac;
}

// ------------------------------------------------------------------
// SCD30 setup
// ------------------------------------------------------------------
void scd30_setup() {
  Serial.println("Adafruit SCD30 setup");

  if (!scd30.begin()) {
    Serial.println("Failed to find SCD30 chip");
    while (1) {
      delay(1000);
    }
  }
  Serial.println("SCD30 Found!");

  Serial.print("Measurement Interval: ");
  Serial.print(scd30.getMeasurementInterval());
  Serial.println(" seconds");
}

// ------------------------------------------------------------------
// Setup
// ------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  // We only use WiFi to be able to call WiFi.macAddress()
  WiFi.mode(WIFI_MODE_STA);

  String macStr = getMacString();
  Serial.print("ESP32 MAC: ");
  Serial.println(macStr);

  // Start Bluetooth Classic Serial
  // Device name can include part of MAC for easier identification when pairing
  String btName = "ESP32_CO2_" + macStr.substring(macStr.length() - 5); // e.g. last 5 chars
  SerialBT.begin(btName);  // visible Bluetooth name
  Serial.print("Bluetooth device name: ");
  Serial.println(btName);
  Serial.println("Now you can pair it with your laptop.");

  scd30_setup();
}

// ------------------------------------------------------------------
// Loop: read SCD30 and send JSON over BluetoothSerial
// ------------------------------------------------------------------
void loop() {
  if (scd30.dataReady()) {

    if (!scd30.read()) {
      Serial.println("Error reading SCD30 data");
      delay(1000);
      return;
    }

    float co2 = scd30.CO2;
    float temp = scd30.temperature;
    float rh = scd30.relative_humidity;

    String macStr = getMacString();

    // JSON payload, include CO2 and MAC
    // Matches your server’s expectation {"int_10":<co2>, "mac":"..."}
    String payload = "{";
    payload += "\"int_10\":" + String(co2, 1);   // one decimal place
    payload += ",\"mac\":\"" + macStr + "\"";
    payload += "}";

    // Terminate with newline so Python can use readline()
    payload += "\n";

    // Send out over Bluetooth serial
    SerialBT.print(payload);

    // Optional debug to USB serial
    Serial.print("Sent: ");
    Serial.print(payload);

  } else {
    // Wait a bit and check again
    delay(1000);
  }
}
