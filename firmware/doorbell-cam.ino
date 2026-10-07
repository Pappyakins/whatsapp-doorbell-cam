// WhatsApp Doorbell Cam — ESP32-CAM (AI-Thinker) firmware.
//
// Behaviour:
//   * Deep-sleeps at ~microamps. A PIR on GPIO 13 wakes it (EXT0, HIGH).
//   * On wake: captures a JPEG, POSTs it to the home server, blinks the
//     flash LED once, then goes back to deep sleep.
//   * On power-on: sends one "doorbell online" photo, then sleeps.
//
// Copy config.h.example -> config.h and fill in your values.
// config.h is gitignored — never commit Wi-Fi credentials or the token.

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "mbedtls/base64.h"
#include "config.h"

// ---- AI-Thinker ESP32-CAM pins ----
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define PIR_GPIO          13          // HC-SR501 OUT -> GPIO13
#define FLASH_GPIO         4          // on-board flash LED
#define WIFI_TIMEOUT_MS   12000

static void go_to_sleep() {
  Serial.println("sleeping...");
  Serial.flush();
  esp_sleep_enable_ext0_wakeup((gpio_num_t)PIR_GPIO, 1);  // wake on PIR HIGH
  esp_deep_sleep_start();
}

static bool init_camera() {
  camera_config_t cfg;
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.pin_d0 = Y2_GPIO_NUM;  cfg.pin_d1 = Y3_GPIO_NUM;
  cfg.pin_d2 = Y4_GPIO_NUM;  cfg.pin_d3 = Y5_GPIO_NUM;
  cfg.pin_d4 = Y6_GPIO_NUM;  cfg.pin_d5 = Y7_GPIO_NUM;
  cfg.pin_d6 = Y8_GPIO_NUM;  cfg.pin_d7 = Y9_GPIO_NUM;
  cfg.pin_xclk = XCLK_GPIO_NUM; cfg.pin_pclk = PCLK_GPIO_NUM;
  cfg.pin_vsync = VSYNC_GPIO_NUM; cfg.pin_href = HREF_GPIO_NUM;
  cfg.pin_sscb_sda = SIOD_GPIO_NUM; cfg.pin_sscb_scl = SIOC_GPIO_NUM;
  cfg.pin_pwdn = PWDN_GPIO_NUM; cfg.pin_reset = RESET_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size = FRAMESIZE_SVGA;       // 800x600 — good detail, small file
  cfg.jpeg_quality = 10;                 // 0(best)..63(worst)
  cfg.fb_count = 1;
  cfg.fb_location = CAMERA_FB_IN_PSRAM;
  cfg.grab_mode = CAMERA_GRAB_LATEST;
  return esp_camera_init(&cfg) == ESP_OK;
}

// base64-encode raw bytes into an Arduino String
static bool b64encode(const uint8_t *in, size_t in_len, String &out) {
  size_t out_len = 0;
  if (mbedtls_base64_encode(NULL, 0, &out_len, in, in_len) != MBEDTLS_ERR_BASE64_BUFFER_TOO_SMALL)
    return false;
  out.reserve(out_len + 32);
  // build in chunks to avoid one giant temporary buffer
  const size_t CHUNK = 3 * 1024;
  uint8_t *tmp = (uint8_t *)malloc(out_len + 1);
  if (!tmp) return false;
  size_t olen = 0;
  bool ok = mbedtls_base64_encode(tmp, out_len + 1, &olen, in, in_len) == 0;
  if (ok) { tmp[olen] = 0; out = "data:image/jpeg;base64," + String((char *)tmp); }
  free(tmp);
  return ok;
}

static bool send_photo(const String &b64photo) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_TIMEOUT_MS)
    delay(250);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi failed");
    return false;
  }
  Serial.print("wifi ok, rssi ");
  Serial.println(WiFi.RSSI());

  HTTPClient http;
  http.begin(SERVER_URL);                      // e.g. http://192.168.2.139:8099/api/doorbell-photo
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);
  String body = "{\"token\":\"" + String(DEVICE_TOKEN) + "\",\"photo\":\"" + b64photo + "\"}";
  int code = http.POST(body);
  Serial.print("POST -> ");
  Serial.println(code);
  String resp = http.getString();
  Serial.println(resp);
  http.end();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  return code == 200;
}

void setup() {
  Serial.begin(115200);
  delay(100);
  pinMode(FLASH_GPIO, OUTPUT);
  digitalWrite(FLASH_GPIO, LOW);
  pinMode(PIR_GPIO, INPUT);

  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  if (cause != ESP_SLEEP_WAKEUP_EXT0 && cause != ESP_SLEEP_WAKEUP_UNDEFINED) {
    go_to_sleep();  // woke for another reason — back to sleep
  }

  if (!init_camera()) {
    Serial.println("camera init failed");
    go_to_sleep();
  }

  // let auto-exposure settle, then grab
  delay(400);
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("capture failed");
    go_to_sleep();
  }
  Serial.print("captured ");
  Serial.print(fb->len);
  Serial.println(" bytes");

  String b64;
  bool ok = b64encode(fb->buf, fb->len, b64);
  esp_camera_fb_return(fb);
  if (ok) ok = send_photo(b64);

  if (ok) {  // blink flash to acknowledge
    digitalWrite(FLASH_GPIO, HIGH);
    delay(250);
    digitalWrite(FLASH_GPIO, LOW);
  }
  go_to_sleep();
}

void loop() { /* never reached */ }
