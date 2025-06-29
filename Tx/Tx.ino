#include <heltec_unofficial.h>

#define FREQUENCY        916.5
#define BANDWIDTH        0
#define SPREADING_FACTOR 9
#define TRANSMIT_POWER   21

const char* MY_ID = "TX4";  // ส่ง ID นี้รัวๆ

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
}

void loop() {
  heltec_loop();

  int status = radio.transmit(MY_ID);
  if (status == RADIOLIB_ERR_NONE) {
    both.printf("📡 Sent: %s ✅\n", MY_ID);
  } else {
    both.printf("❌ Send Fail (%d)\n", status);
  }

  delay(1); // ป้องกัน CPU overheat / watchdog reset
}
