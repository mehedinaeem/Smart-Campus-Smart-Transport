#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

const char* WIFI_SSID = "Connecting..._5G";
const char* WIFI_PASSWORD = "12341234";
const char* SERVER_URL = "http://192.168.0.196:8000/api/device/telemetry/";

const char* BUS_IDENTIFIER = "BUS-01";
const char* API_KEY = "";

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

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
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

  String payload = buildPayload();

  Serial.println("Sending payload:");
  Serial.println(payload);

  int responseCode = http.POST(payload);
  String responseBody = http.getString();

  Serial.print("HTTP Response Code: ");
  Serial.println(responseCode);
  Serial.print("Response Body: ");
  Serial.println(responseBody);

  http.end();

  if (responseCode <= 0) {
    Serial.println("Failed to send telemetry");
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(GPS_BAUD_RATE, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  Serial.println("Starting ESP32 GPS tracker...");
  connectToWifi();
}

void loop() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  if (gps.location.isValid()) {
    Serial.print("Lat: ");
    Serial.println(gps.location.lat(), 6);
    Serial.print("Lng: ");
    Serial.println(gps.location.lng(), 6);
    Serial.print("Speed (km/h): ");
    Serial.println(gps.speed.kmph(), 2);
    Serial.print("Satellites: ");
    Serial.println(gps.satellites.isValid() ? gps.satellites.value() : 0);
  }

  unsigned long now = millis();
  if (gps.location.isValid() && now - lastSendAt >= SEND_INTERVAL_MS) {
    sendTelemetry();
    lastSendAt = now;
  }
}