#include <heltec_unofficial.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <map>

// 🔧 LoRa config
#define BANDWIDTH        0
#define SPREADING_FACTOR 9

// 🌀 ความถี่ที่ RX จะวนรับทีละรอบ
const float freqs[] = {915.0, 915.5, 916.0,916.5};
int currentFreqIndex = 0;
unsigned long lastHopTime = 0;
unsigned long hopInterval = 500;  // ms

// 🌐 UDP config
WiFiUDP udp;
const char* udp_host = "172.20.0.89";
const int udp_port = 2500;

// 📡 WiFi BSSID ที่ต้องการอ่าน RSSI
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
  both.println("🚀 RX Real-time: Multi-Frequency LoRa + WiFi RSSI → UDP");

  // ☑️ Init LoRa
  if (radio.begin() != RADIOLIB_ERR_NONE) {
    both.println("❌ LoRa init failed!");
    while (true);
  }

  radio.setBandwidth(BANDWIDTH);
  radio.setSpreadingFactor(SPREADING_FACTOR);
  radio.setFrequency(freqs[currentFreqIndex]);
  radio.startReceive();

  // ☑️ Init WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin("PNU@WiFi", "");  // 🔁 เปลี่ยน SSID และรหัสหากจำเป็น

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

  // ✅ รับ LoRa ถ้ามี
  String received;
  int status = radio.receive(received);
  if (status == RADIOLIB_ERR_NONE) {
    int rssi = radio.getRSSI();
    String message = received + ": " + String(rssi) ;
    sendUDPMessage(message);
    radio.startReceive();  // กลับไปฟังใหม่
  }

  // 🔁 สลับความถี่ทุก hopInterval ms
  if (millis() - lastHopTime > hopInterval) {
    currentFreqIndex = (currentFreqIndex + 1) % (sizeof(freqs) / sizeof(freqs[0]));
    radio.setFrequency(freqs[currentFreqIndex]);
    radio.startReceive();
    lastHopTime = millis();
    both.printf("🔄 Switched to %.1f MHz\n", freqs[currentFreqIndex]);
  }

  // 📶 สแกน WiFi BSSID ที่สนใจ
  static unsigned long lastScanTime = 0;
  const unsigned long scanInterval = 2000;

  if (millis() - lastScanTime > scanInterval) {
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
