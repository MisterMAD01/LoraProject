// ✅ ปรับโค้ดให้ไม่ต้อง reboot หลังบันทึกค่า Web Config
// - เปิด SoftAP "RX_Config" ตลอดเวลา พร้อมใช้งาน
// - หน้าเว็บรองรับ / /home /config /reset พร้อม UI ภาษาอังกฤษและสไตล์ CSS

#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebServer.h>
#include <EEPROM.h>
#include <heltec_unofficial.h>
#include <map>

#define EEPROM_SIZE 128
#define SSID_ADDR   0
#define PASS_ADDR   32
#define IP_ADDR     64
#define PORT_ADDR   80

WiFiUDP udp;
WebServer server(80);
bool configMode = false;
bool udpReady = false;

String wifi_ssid, wifi_pass, udp_ip;
uint16_t udp_port;

#define BANDWIDTH 0
#define SPREADING_FACTOR 9
const float freqs[] = {915.0, 915.5, 916.0, 916.5};
int currentFreqIndex = 0;
unsigned long lastHopTime = 0;
unsigned long hopInterval = 500;

std::map<String, String> fixedWiFiLabels = {
  {"9C:8C:D8:05:25:C0", "WiFi1"},
  {"9C:8C:D8:03:B2:A0", "WiFi2"},
  {"90:4C:81:42:00:E0", "WiFi3"},
  {"E8:26:89:B1:99:20", "WiFi4"},
  {"E8:26:89:B0:BC:80", "WiFi5"},
  {"9C:8C:D8:02:F6:60", "WiFi6"}
};

String style = "<style>body{font-family:sans-serif;margin:20px;padding:10px;}"
               "input,select,button{padding:8px;margin:5px;width:95%;max-width:400px;}"
               "form{margin-bottom:20px;}"
               "a{margin-right:10px;}" 
               "h2{color:#007bff;}"
               "button{background:#007bff;color:white;border:none;border-radius:5px;}"
               "button.danger{background:red;}</style>";

void saveStringToEEPROM(int addr, const String& value, int maxLen) {
  for (int i = 0; i < maxLen; ++i) EEPROM.write(addr + i, i < value.length() ? value[i] : 0);
}

String readStringFromEEPROM(int addr, int maxLen) {
  String value;
  for (int i = 0; i < maxLen; ++i) {
    char c = EEPROM.read(addr + i);
    if (c == 0 || c == 255) break;
    value += c;
  }
  return value;
}

void saveSettingsToEEPROM(String ssid, String pass, String ip, uint16_t port) {
  EEPROM.begin(EEPROM_SIZE);
  saveStringToEEPROM(SSID_ADDR, ssid, 32);
  saveStringToEEPROM(PASS_ADDR, pass, 32);
  saveStringToEEPROM(IP_ADDR, ip, 16);
  EEPROM.write(PORT_ADDR, port >> 8);
  EEPROM.write(PORT_ADDR + 1, port & 0xFF);
  EEPROM.commit();
}

void clearEEPROM() {
  EEPROM.begin(EEPROM_SIZE);
  for (int i = 0; i < EEPROM_SIZE; ++i) EEPROM.write(i, 0);
  EEPROM.commit();
}

void loadSettingsFromEEPROM() {
  EEPROM.begin(EEPROM_SIZE);
  wifi_ssid = readStringFromEEPROM(SSID_ADDR, 32);
  wifi_pass = readStringFromEEPROM(PASS_ADDR, 32);
  udp_ip = readStringFromEEPROM(IP_ADDR, 16);
  udp_port = (EEPROM.read(PORT_ADDR) << 8) | EEPROM.read(PORT_ADDR + 1);
}

void connectWiFiAndUDP() {
  WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());
  both.print("Connecting to WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500); both.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    both.println(" ✅ Connected!");
    udp.begin(WiFi.localIP(), udp_port);
    udpReady = true;
  } else {
    both.println(" ❌ Failed to connect.");
    udpReady = false;
  }

  both.print("🌐 Device IP: "); both.println(WiFi.localIP());
}

void startWebServer() {
  server.on("/", []() {
    int n = WiFi.scanNetworks();
    String options = "";
    for (int i = 0; i < n; i++) {
      String ssid = WiFi.SSID(i);
      options += "<option value='" + ssid + "'>" + ssid + "</option>";
    }

    String html = style + "<h2>📡 WiFi Config</h2>"
      "<form action='/save' method='GET'>"
      "SSID: <select name='ssid'>" + options + "</select><br>"
      "Password: <input name='pass' type='password'><br>"
      "UDP IP: <input name='ip'><br>"
      "UDP Port: <input name='port' type='number'><br>"
      "<button type='submit'> Save & Apply</button></form>"
      "<form action='/reset' method='POST'>"
      "<button class='danger'> Reset Config</button></form>"
      "<a href='/home'> Home</a> | <a href='/config'> Config</a>";
    server.send(200, "text/html", html);
  });

  server.on("/save", []() {
    wifi_ssid = server.arg("ssid");
    wifi_pass = server.arg("pass");
    udp_ip = server.arg("ip");
    udp_port = server.arg("port").toInt();
    saveSettingsToEEPROM(wifi_ssid, wifi_pass, udp_ip, udp_port);
    connectWiFiAndUDP();
    server.send(200, "text/html", style + "<p> Saved! <a href='/home'>Go to Home</a></p>");
  });

  server.on("/reset", HTTP_POST, []() {
    clearEEPROM();
    server.send(200, "text/html", style + "<p>🧹 Config Cleared! Please refresh and reconfigure.<br><a href='/'>Back</a></p>");
  });

  server.on("/config", []() {
    String html = style + "<h2> Config</h2>"
      "<form action='/save' method='GET'>"
      "SSID: <input name='ssid' value='" + wifi_ssid + "'><br>"
      "Password: <input name='pass' value='" + wifi_pass + "'><br>"
      "UDP IP: <input name='ip' value='" + udp_ip + "'><br>"
      "UDP Port: <input name='port' type='number' value='" + String(udp_port) + "'><br>"
      "<button type='submit'> Update</button></form>"
      "<form action='/reset' method='POST'>"
      "<button class='danger'> Reset Config</button></form>"
      "<a href='/home'> Home</a> | <a href='/'> WiFi</a>";
    server.send(200, "text/html", html);
  });

  server.on("/home", []() {
    String html = style + "<h2>🏠 Status</h2>"
      "<p><b>Connected SSID:</b> " + wifi_ssid + "<br>"
      "<b>UDP IP:</b> " + udp_ip + "<br>"
      "<b>UDP Port:</b> " + String(udp_port) + "<br>"
      "<b>Device IP:</b> " + WiFi.localIP().toString() + "<br>"
      "<b>SoftAP IP:</b> " + WiFi.softAPIP().toString() + "</p>"
      "<a href='/'> WiFi</a> | <a href='/config'> Config</a>";
    server.send(200, "text/html", html);
  });

  server.begin();
}

void sendUDPMessage(const String& message) {
  if (!udpReady) return;
  udp.beginPacket(udp_ip.c_str(), udp_port);
  udp.println(message);
  udp.endPacket();
  both.println("📤 UDP Sent: " + message);
}

void setup() {
  heltec_setup();
  both.println("🚀 RX Web Config + LoRa + WiFi RSSI");
  loadSettingsFromEEPROM();
  WiFi.softAP("RX_Config", "12345678");
  startWebServer();
  connectWiFiAndUDP();

  if (radio.begin() != RADIOLIB_ERR_NONE) {
    both.println("❌ LoRa init failed! "); while (true);
  }
  radio.setBandwidth(BANDWIDTH);
  radio.setSpreadingFactor(SPREADING_FACTOR);
  radio.setFrequency(freqs[currentFreqIndex]);
  radio.startReceive();
}

void loop() {
  heltec_loop();
  server.handleClient();
  if (!udpReady) return;

  String received;
  int status = radio.receive(received);
  if (status == RADIOLIB_ERR_NONE) {
    int rssi = radio.getRSSI();
    sendUDPMessage(received + ": " + String(rssi));
    radio.startReceive();
  }

  if (millis() - lastHopTime > hopInterval) {
    currentFreqIndex = (currentFreqIndex + 1) % (sizeof(freqs)/sizeof(freqs[0]));
    radio.setFrequency(freqs[currentFreqIndex]);
    radio.startReceive();
    lastHopTime = millis();
    both.printf("🔄 Switched to %.1f MHz\n", freqs[currentFreqIndex]);
  }

  static unsigned long lastScanTime = 0;
  if (millis() - lastScanTime > 2000) {
    int n = WiFi.scanNetworks(false, true);
    for (int i = 0; i < n; ++i) {
      String bssid = WiFi.BSSIDstr(i);
      if (fixedWiFiLabels.count(bssid)) {
        String msg = fixedWiFiLabels[bssid] + ": " + String(WiFi.RSSI(i));
        sendUDPMessage(msg);
      }
    }
    lastScanTime = millis();
  }
}
