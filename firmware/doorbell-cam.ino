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
//
// Setup app: settings can also be written over Bluetooth by the
// JakinsCraft ESP Setup app (see PROVISIONING.md). Values stored by the
// app live in NVS flash and OVERRIDE config.h; config.h stays as the
// first-flash fallback. Provisioning only starts on a manual power-on
// when Wi-Fi cannot connect — never on a PIR wake — and gives up after
// 2 tries so a dead router cannot drain the battery.

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include "esp_mac.h"
#include "mbedtls/base64.h"
#include "config.h"

// Optional: give this camera a name ("Front Door", "Back Door", ...) in
// config.h and it is sent with every photo so the WhatsApp message says
// which camera fired. Old config.h files without it still compile.
#ifndef CAMERA_NAME
#define CAMERA_NAME ""
#endif

// Optional: WhatsApp number this camera should alert, digits only with
// country code (e.g. "14165550123"). The server only honors numbers on
// its allowlist (doorbell.json); anything else falls back to the default
// notify_to there. Empty = use the server default.
#ifndef NOTIFY_TO
#define NOTIFY_TO ""
#endif

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

// ---- effective config: config.h defaults, NVS (app-written) wins ----
static String cfgSsid   = WIFI_SSID;
static String cfgPass   = WIFI_PASS;
static String cfgServer = SERVER_URL;
static String cfgToken  = DEVICE_TOKEN;
static String cfgName   = CAMERA_NAME;
static String cfgTo     = NOTIFY_TO;
static bool   g_powerOn = false;   // true when this boot is a manual power-on

static void load_config() {
  Preferences p;
  if (p.begin("doorcfg", true)) {
    cfgSsid   = p.getString("ssid",   cfgSsid);
    cfgPass   = p.getString("pass",   cfgPass);
    cfgServer = p.getString("server", cfgServer);
    cfgToken  = p.getString("token",  cfgToken);
    cfgName   = p.getString("name",   cfgName);
    cfgTo     = p.getString("to",     cfgTo);
    p.end();
  }
  Serial.print("config: ssid=");
  Serial.print(cfgSsid);
  Serial.print(" name=");
  Serial.println(cfgName);
}

static void go_to_sleep() {
  Serial.println("sleeping...");
  Serial.flush();
  esp_sleep_enable_ext0_wakeup((gpio_num_t)PIR_GPIO, 1);  // wake on PIR HIGH
  esp_deep_sleep_start();
}

// ---- BLE provisioning (JakinsCraft ESP Setup app, see PROVISIONING.md) ----
// One writable characteristic per field; write "APPLY" to the control
// characteristic to save everything to NVS and restart, "ERASE" to wipe
// the stored settings and restart. Read the control characteristic for
// status: "ready", "saved" or "erased".
#define PROV_SERVICE_UUID  "8d4f0001-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_SSID_UUID     "8d4f0002-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_PASS_UUID     "8d4f0003-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_NAME_UUID     "8d4f0004-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_TO_UUID       "8d4f0005-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_SERVER_UUID   "8d4f0006-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_TOKEN_UUID    "8d4f0007-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_CONTROL_UUID  "8d4f0008-3c2a-4b5e-9f1a-2b3c4d5e6f70"
#define PROV_WINDOW_MS     300000    // 5 minutes, then give up and sleep
#define PROV_MAX_TRIES     2

RTC_DATA_ATTR static int provTries = 0;  // survives deep sleep + restart

static String pendSsid, pendPass, pendName, pendTo, pendServer, pendToken;
static BLECharacteristic *provControl = nullptr;
static volatile bool provDone = false;

class ProvFieldCallbacks : public BLECharacteristicCallbacks {
  String *slot;
public:
  ProvFieldCallbacks(String *s) : slot(s) {}
  void onWrite(BLECharacteristic *c) override { *slot = c->getValue().c_str(); }
};

class ProvControlCallbacks : public BLECharacteristicCallbacks {
public:
  void onWrite(BLECharacteristic *c) override {
    String cmd = c->getValue().c_str();
    cmd.trim();
    if (cmd == "APPLY") {
      Preferences p;
      if (p.begin("doorcfg", false)) {
        if (pendSsid.length())   p.putString("ssid", pendSsid);
        if (pendPass.length())   p.putString("pass", pendPass);
        if (pendServer.length()) p.putString("server", pendServer);
        if (pendToken.length())  p.putString("token", pendToken);
        p.putString("name", pendName);   // may be blanked on purpose
        p.putString("to", pendTo);
        p.end();
      }
      provControl->setValue("saved");
      Serial.println("provisioning: saved, restarting");
      provDone = true;
    } else if (cmd == "ERASE") {
      Preferences p;
      if (p.begin("doorcfg", false)) { p.clear(); p.end(); }
      provControl->setValue("erased");
      Serial.println("provisioning: erased, restarting");
      provDone = true;
    }
  }
};

static BLECharacteristic *prov_field(BLEService *svc, const char *uuid,
                                     const String &initial, String *slot) {
  BLECharacteristic *ch = svc->createCharacteristic(
      uuid, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ch->setValue(initial.c_str());
  *slot = initial;
  ch->setCallbacks(new ProvFieldCallbacks(slot));
  return ch;
}

// Run BLE setup mode for up to PROV_WINDOW_MS. Returns when settings were
// applied/erased (caller restarts) or the window timed out (caller sleeps).
static void run_provisioning() {
  Serial.println("provisioning: BLE setup mode");
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  pendSsid = cfgSsid;  pendPass = "";  pendName = cfgName;
  pendTo = cfgTo;      pendServer = cfgServer;  pendToken = cfgToken;

  String advName = "JakinsCam-";
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_BT);
  char suffix[5];
  snprintf(suffix, sizeof(suffix), "%02X%02X", mac[4], mac[5]);
  advName += suffix;

  BLEDevice::init(advName.c_str());
  BLEServer *server = BLEDevice::createServer();
  BLEService *svc = server->createService(PROV_SERVICE_UUID);
  prov_field(svc, PROV_SSID_UUID, cfgSsid, &pendSsid);
  prov_field(svc, PROV_PASS_UUID, "", &pendPass);          // never echo the password back
  prov_field(svc, PROV_NAME_UUID, cfgName, &pendName);
  prov_field(svc, PROV_TO_UUID, cfgTo, &pendTo);
  prov_field(svc, PROV_SERVER_UUID, cfgServer, &pendServer);
  prov_field(svc, PROV_TOKEN_UUID, cfgToken, &pendToken);
  provControl = svc->createCharacteristic(
      PROV_CONTROL_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  provControl->setValue("ready");
  provControl->setCallbacks(new ProvControlCallbacks());
  svc->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(PROV_SERVICE_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();

  unsigned long t0 = millis();
  while (!provDone && millis() - t0 < PROV_WINDOW_MS) {
    digitalWrite(FLASH_GPIO, HIGH);  // slow heartbeat blink: setup mode
    delay(60);
    digitalWrite(FLASH_GPIO, LOW);
    delay(940);
  }
  BLEDevice::deinit(true);
  if (provDone) {
    delay(300);  // let the app read the final status
    ESP.restart();
  }
  Serial.println("provisioning: window closed with no save");
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
  if (esp_camera_init(&cfg) != ESP_OK) return false;

  // ---- image settings dialed in via the tuner (2026-10-17) ----
  // White balance on, WB mode Home, brightness -1, contrast 0,
  // saturation 0, manual exposure 460, manual gain 22, lens correction on.
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_whitebal(s, 1);      // auto white balance on
    s->set_awb_gain(s, 1);      // white-balance gain on
    s->set_wb_mode(s, 4);       // 4 = home (warm indoor light)
    s->set_brightness(s, -1);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_exposure_ctrl(s, 0); // manual exposure...
    s->set_aec_value(s, 460);   // ...at 460
    s->set_gain_ctrl(s, 0);     // manual gain...
    s->set_agc_gain(s, 22);     // ...at 22
    s->set_lenc(s, 1);          // lens shading correction on
  }
  return true;
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
  WiFi.begin(cfgSsid.c_str(), cfgPass.c_str());
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_TIMEOUT_MS)
    delay(250);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi failed");
    return false;
  }
  provTries = 0;  // Wi-Fi works — reset the provisioning try counter
  Serial.print("wifi ok, rssi ");
  Serial.println(WiFi.RSSI());

  WiFiClientSecure secureClient;
  secureClient.setInsecure();
  HTTPClient http;
  if (cfgServer.startsWith("https://")) {
    http.begin(secureClient, cfgServer);       // e.g. https://rserver.beagle-sunfish.ts.net/api/doorbell-photo
  } else {
    http.begin(cfgServer);                     // e.g. http://192.168.2.139:8099/api/doorbell-photo
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);
  String body = "{\"token\":\"" + cfgToken + "\",\"name\":\"" + cfgName + "\",\"to\":\"" + cfgTo + "\",\"photo\":\"" + b64photo + "\"}";
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

  load_config();

  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  g_powerOn = (cause == ESP_SLEEP_WAKEUP_UNDEFINED);
  if (cause != ESP_SLEEP_WAKEUP_EXT0 && cause != ESP_SLEEP_WAKEUP_UNDEFINED) {
    go_to_sleep();  // woke for another reason — back to sleep
  }

  if (!init_camera()) {
    Serial.println("camera init failed");
    go_to_sleep();
  }

  // let auto-exposure and white balance settle, then grab
  delay(1000);
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
  } else if (g_powerOn && provTries < PROV_MAX_TRIES) {
    // Manual power-on and Wi-Fi failed: offer BLE setup (bounded tries,
    // so a router outage on battery can't loop forever). Restarts itself
    // if the app saves or erases; on timeout we fall through to sleep.
    provTries++;
    run_provisioning();
  }
  go_to_sleep();
}

void loop() { /* never reached */ }
