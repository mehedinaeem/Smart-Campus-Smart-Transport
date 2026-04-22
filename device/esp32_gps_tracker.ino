#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://YOUR_SERVER_HOST:8000/api/device/telemetry/";

const char* BUS_IDENTIFIER = "esp32-bus-101";
const char* API_KEY = "secret-key";

TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

constexpr uint32_t GPS_BAUD_RATE = 9600;
constexpr uint32_t SEND_INTERVAL_MS = 10000;
constexpr int GPS_RX_PIN = 16;
constexpr int GPS_TX_PIN = 17;

unsigned long lastSendAt = 0;

void connectToWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

String buildPayload() {
  String json = "{";
  json += "\"bus_identifier\":\"" + String(BUS_IDENTIFIER) + "\",";
  json += "\"api_key\":\"" + String(API_KEY) + "\",";
  json += "\"latitude\":" + String(gps.location.lat(), 6) + ",";
  json += "\"longitude\":" + String(gps.location.lng(), 6) + ",";
  json += "\"speed\":" + String(gps.speed.kmph(), 2) + ",";
  json += "\"heading\":" + String(gps.course.isValid() ? gps.course.deg() : 0.0, 2) + ",";
  json += "\"ignition\":true";
  json += "}";
  return json;
}

void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    connectToWifi();
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  const String payload = buildPayload();
  const int responseCode = http.POST(payload);
  http.end();

  if (responseCode <= 0) {
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(GPS_BAUD_RATE, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  connectToWifi();
}

void loop() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  const unsigned long now = millis();
  if (gps.location.isValid() && now - lastSendAt >= SEND_INTERVAL_MS) {
    sendTelemetry();
    lastSendAt = now;
  }
}
