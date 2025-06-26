#include <heltec_unofficial.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <map>

#define FREQUENCY        915.0
#define BANDWIDTH        0
#define SPREADING_FACTOR 9

WiFiUDP udp;
const char* udp_host = "10.105.5.44";
const int udp_port = 2547;

std::map<String, String> fixedWiFiLabels = {
  {"9C:8C:D8:05:25:C0", "WiFi1"},
  {"9C:8C:D8:03:B2:A0", "WiFi2"},
  {"90:4C:81:42:00:E0", "WiFi3"},
  {"E8:26:89:B1:99:20", "WiFi4"},
  {"E8:26:89:B0:BC:80", "WiFi5"},
  {"9C:8C:D8:02:F6:60", "WiFi6"}
};

void sendUDPMessage(const String& message) {
  udp.beginPacket(udp_host, udp_port);
  udp.println(message);
  udp.endPacket();
  both.println("📤 UDP Sent: " + message);
}

void setup() {
  heltec_setup();
  both.println("🚀 RX Real-time: LoRa + WiFi RSSI → UDP");

  if (radio.begin() != RADIOLIB_ERR_NONE) {
    both.println("❌ LoRa init failed!");
    while (true);
  }
  radio.setFrequency(FREQUENCY);
  radio.setBandwidth(BANDWIDTH);
  radio.setSpreadingFactor(SPREADING_FACTOR);
  radio.startReceive();

  WiFi.mode(WIFI_STA);
  WiFi.begin("park kin hum", "");  // เปลี่ยนชื่อ WiFi และรหัสให้ถูกต้อง

  both.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    both.print(".");
  }
  both.println(" ✅ Connected!");

  udp.begin(WiFi.localIP(), udp_port);
}

void loop() {
  heltec_loop();

  // ✅ 1. รับข้อมูล LoRa และส่ง UDP ทันที
  String received;
  int status = radio.receive(received);
  if (status == RADIOLIB_ERR_NONE) {
    int rssi = radio.getRSSI();
    String message = received + ": " + String(rssi);
    sendUDPMessage(message);
    radio.startReceive();  // กลับไปฟังใหม่ทันที
  }

  // ✅ 2. สแกน WiFi และส่งทุกตัวที่อยู่ใน fixedWiFiLabels
  static unsigned long lastScanTime = 0;
  if (millis() - lastScanTime > 1000) {
    int n = WiFi.scanNetworks(false, true);
    for (int i = 0; i < n; ++i) {
      String bssid = WiFi.BSSIDstr(i);
      int rssi = WiFi.RSSI(i);

      if (fixedWiFiLabels.count(bssid)) {
        String label = fixedWiFiLabels[bssid];
        String msg = label + ": " + String(rssi);
        sendUDPMessage(msg);
      }
    }
    lastScanTime = millis();
  }
}
