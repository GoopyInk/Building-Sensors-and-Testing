// Switch to MQTT design to allow for improved accuracy and connection among components. 
// Essentially remove all current pieces. 
// Figure out a better setup for the Pi wifi configuration and connection  
// 

// WiFi libraries
#include <WiFi.h>
#include <WiFiMulti.h>
#include <WiFiSTA.h>
// #include "esp_wifi.h"

// Sensor Libraries
#include <Adafruit_SCD30.h>
#include <Adafruit_SHT4x.h>


// WiFi information
const char* ssid = "modelbuildingpi";
const char* password = "ModelBuildingPi!";
const uint16_t port = 5000;

// Pi IP Address 100.84.28.153
const char* PI_IP = "127.0.0.1";
WiFiMulti WiFiMulti;

// Sensors instantiation
Adafruit_SHT4x sht4 = Adafruit_SHT4x();
Adafruit_SCD30 scd30 = Adafruit_SCD30();

/*
initial Setup for the wifi to connect to our rasberry pi
*/
void WiFi_Setup() {
  // Setting the Baud to be 115200
  Serial.begin(115200);
  
  
  while (!Serial) {
    delay(10);
  }

  // Login to the host WiFi
  WiFiMulti.addAP(ssid, password);
  Serial.println();

  // Delay until a connection is made
  int total_delay = 0;
  while (WiFiMulti.run() != WL_CONNECTED){
      Serial.print(".");
      delay(1000);
      total_delay += 1000;
      // ends the function after 60 seconds of delay
      Serial.print(total_delay);
      if (total_delay > 60000) {
        return;
      }
    }

  // Connection complete,
  Serial.println("WiFi Connected)");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // WiFi.softAP("MyESP32AP");
  

  delay(1000);


}

/*
Initial Setup for our Carbon Dioxide and Temperature Sensor, SCD30
*/
void scd30_setup() {
  // Setting the Baud to be 115200
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Serial.println("Adafruit SCD30 setup");

  // Try to initialize!
  if (!scd30.begin()) {
    Serial.println("Failed to find SCD30 chip");
    return;
  }
  Serial.println("SCD30 Found!");


  // if (!scd30.setMeasurementInterval(10)){
  //   Serial.println("Failed to set measurement interval");
  //   while(1){ delay(10);}
  // }
  // Scans every 2 Seconds
  Serial.print("Measurement Interval: ");
  Serial.print(scd30.getMeasurementInterval());
  Serial.println(" seconds");
}
/*
void sht40_setup() {
  // Setting the Baud to be 115200
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Serial.println("Adafruit SHT40 setup");
  if (!sht4.begin()) {
    Serial.println("Couldn't find SHT40");
    break;
  }
  Serial.println("Found SHT40 sensor");
  Serial.print("Serial number 0x");
  Serial.println(sht4.readSerial(), HEX);

  // You can have 3 different precisions, higher precision takes longer
  sht4.setPrecision(SHT4X_HIGH_PRECISION);
  switch (sht4.getPrecision()) {
    case SHT4X_HIGH_PRECISION:
      Serial.println("High precision");
      break;
    case SHT4X_MED_PRECISION:
      Serial.println("Med precision");
      break;
    case SHT4X_LOW_PRECISION:
      Serial.println("Low precision");
      break;
  }

  // You can have 6 different heater settings
  // higher heat and longer times uses more power
  // and reads will take longer too!
}
*/

void setup() {
  // put your setup code here, to run once:
  WiFi_Setup();
  scd30_setup();
  //sht40_setup();
}

void loop() {
  // put your main code here, to run repeatedly:
  // wifi_sta_list_t wifi_sta_list;
  // tcpip_adapter_sta_list_t adapter_sta_list;
  // memset(&wifi_sta_list, 0, sizeof(wifi_sta_list));
  // memset(&adapter_sta_list, 0, sizeof(adapter_sta_list));
  // esp_wifi_ap_get_sta_list(&wifi_sta_list);
  // tcpip_adapter_get_sta_list(&wifi_sta_list, &adapter_sta_list);
  // tcpip_adapter_sta_info_t station = adapter_sta_list.sta[0];
  // PI_IP = ip4addr_ntoa(&(station.ip)); 

  if (scd30.dataReady()) {
    WiFiClient client; 
    if(!client.connect(PI_IP, port)){
      Serial.println("Connection Failed. Retrying in 10 seconds. ");
      delay(10000); 
      return; 
    }
    String PostData = "esp32={\"int_10\":" + String(scd30.CO2) + "}"; 

    client.println("POST /echo HTTP/1.1");           
	  client.println("Host:  ESP32");           
	  client.println("User-Agent: Arduino/1.0");           
	  client.println("Connection: close");           
	  client.println("Content-Type: application/x-www-form-urlencoded; charset=UTF-8");           
	  client.print("Content-Length: ");           
	  client.println(PostData.length());           
	  client.println();           
	  client.println(PostData);           
	  Serial.println(PostData);           
	  client.stop(); 
  }
  else{
    delay(1000); 
  }
}
