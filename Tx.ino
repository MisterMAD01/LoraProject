#include <heltec_unofficial.h>

#define FREQUENCY        915.0
#define BANDWIDTH        0
#define SPREADING_FACTOR 9
#define TRANSMIT_POWER   21

const char* MY_ID = "TX3";  // 🔁 เปลี่ยนเป็น "TX2", "TX3", "TX4"

uint64_t last_tx = 0;
unsigned long intervalMin = 800;
unsigned long intervalMax = 1500;
unsigned long currentDelay = 1000;

void setup() {
  heltec_setup();
  both.printf("🚀 %s Starting...\n", MY_ID);

  if (radio.begin() != RADIOLIB_ERR_NONE) {
    both.println("❌ LoRa init failed!");
    while (true);
  }

  radio.setFrequency(FREQUENCY);
  radio.setBandwidth(BANDWIDTH);
  radio.setSpreadingFactor(SPREADING_FACTOR);
  radio.setOutputPower(TRANSMIT_POWER);

  currentDelay = random(intervalMin, intervalMax);
}

void loop() {
  heltec_loop();

  if (millis() - last_tx > currentDelay) {
    int status = radio.transmit(MY_ID);
    if (status == RADIOLIB_ERR_NONE) {
      both.printf("📡 Sent: %s ✅\n", MY_ID);
    } else {
      both.printf("❌ Send Fail (%d)\n", status);
    }

    last_tx = millis();
    currentDelay = random(intervalMin, intervalMax);
  }
}
