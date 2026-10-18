// WhatsApp Doorbell Cam — ESP32-CAM (AI-Thinker) firmware.
//
// Behaviour:
//   * Deep-sleeps at ~microamps. A PIR on GPIO 13 wakes it (EXT0, HIGH).
//   * On wake: captures a JPEG, POSTs it to the home server, blinks the
//     flash LED once, then goes back to deep sleep.
//   * On power-on: sends one "doorbell online" photo, then sleeps.
//
// TUNER MODE: on a cold boot (power-on or RST press) the board waits a few
// seconds for any key in the serial monitor. Send one and it starts a WiFi
// web page instead of the doorbell flow. The page shows a live preview plus
// sliders for every image setting (white balance, brightness, contrast,
// saturation, exposure, gain, lens correction). Dial it in, hit Save, and
// the values are stored in flash — the normal doorbell flow uses them from
// then on. PIR wakes skip the wait and go straight to capture.
//
// Copy config.h.example -> config.h and fill in your values.
// config.h is gitignored — never commit Wi-Fi credentials or the token.

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>
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

// ---- tunable image settings (persisted in flash via Preferences) ----
struct TuneSettings {
  int wb;       // white balance on/off (0/1)
  int wbmode;   // 0=auto 1=sunny 2=cloudy 3=office 4=home
  int bright;   // -2..2
  int contrast; // -2..2
  int sat;      // -2..2
  int aec;      // auto exposure on/off (0/1)
  int aecval;   // manual exposure 0..1200 (used when aec=0)
  int agc;      // auto gain on/off (0/1)
  int gain;     // manual gain 0..30 (used when agc=0)
  int lenc;     // lens correction on/off (0/1)
};

static TuneSettings tune;
static Preferences tunePrefs;

static void loadTune() {
  tunePrefs.begin("dtune", true);
  tune.wb       = tunePrefs.getInt("wb", 1);
  tune.wbmode   = tunePrefs.getInt("wbmode", 4);
  tune.bright   = tunePrefs.getInt("bright", 0);
  tune.contrast = tunePrefs.getInt("contrast", 1);
  tune.sat      = tunePrefs.getInt("sat", -1);
  tune.aec      = tunePrefs.getInt("aec", 1);
  tune.aecval   = tunePrefs.getInt("aecval", 300);
  tune.agc      = tunePrefs.getInt("agc", 1);
  tune.gain     = tunePrefs.getInt("gain", 0);
  tune.lenc     = tunePrefs.getInt("lenc", 1);
  tunePrefs.end();
}

static void saveTune() {
  tunePrefs.begin("dtune", false);
  tunePrefs.putInt("wb", tune.wb);
  tunePrefs.putInt("wbmode", tune.wbmode);
  tunePrefs.putInt("bright", tune.bright);
  tunePrefs.putInt("contrast", tune.contrast);
  tunePrefs.putInt("sat", tune.sat);
  tunePrefs.putInt("aec", tune.aec);
  tunePrefs.putInt("aecval", tune.aecval);
  tunePrefs.putInt("agc", tune.agc);
  tunePrefs.putInt("gain", tune.gain);
  tunePrefs.putInt("lenc", tune.lenc);
  tunePrefs.end();
}

static void applyTune() {
  sensor_t *s = esp_camera_sensor_get();
  if (!s) return;
  s->set_whitebal(s, tune.wb);
  s->set_awb_gain(s, tune.wb);
  s->set_wb_mode(s, tune.wbmode);
  s->set_brightness(s, tune.bright);
  s->set_contrast(s, tune.contrast);
  s->set_saturation(s, tune.sat);
  s->set_exposure_ctrl(s, tune.aec);
  s->set_aec2(s, 0);
  if (!tune.aec) s->set_aec_value(s, tune.aecval);
  s->set_gain_ctrl(s, tune.agc);
  if (!tune.agc) s->set_agc_gain(s, tune.gain);
  s->set_lenc(s, tune.lenc);
}

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
  if (esp_camera_init(&cfg) != ESP_OK) return false;
  applyTune();
  return true;
}

// base64-encode raw bytes into an Arduino String
static bool b64encode(const uint8_t *in, size_t in_len, String &out) {
  size_t out_len = 0;
  if (mbedtls_base64_encode(NULL, 0, &out_len, in, in_len) != MBEDTLS_ERR_BASE64_BUFFER_TOO_SMALL)
    return false;
  out.reserve(out_len + 32);
  uint8_t *tmp = (uint8_t *)malloc(out_len + 1);
  if (!tmp) return false;
  size_t olen = 0;
  bool ok = mbedtls_base64_encode(tmp, out_len + 1, &olen, in, in_len) == 0;
  if (ok) { tmp[olen] = 0; out = "data:image/jpeg;base64," + String((char *)tmp); }
  free(tmp);
  return ok;
}

static bool wifi_connect() {
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
  return true;
}

static bool send_photo(const String &b64photo) {
  if (!wifi_connect()) return false;

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

// ------------------------------ tuner mode ------------------------------
static WebServer tunerServer(80);

static const char TUNER_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Doorbell Cam Tuner</title>
<style>
body{font-family:sans-serif;max-width:640px;margin:auto;padding:12px;background:#111;color:#eee}
img{width:100%;border:1px solid #444}
.row{margin:10px 0}
label{display:inline-block;width:170px}
input[type=range]{width:200px;vertical-align:middle}
.val{display:inline-block;width:50px;text-align:right;color:#8f8}
button{font-size:18px;padding:12px 28px;margin:14px 0;background:#2a7;color:#fff;border:0;border-radius:6px}
select{font-size:16px;padding:4px}
.hint{color:#999;font-size:13px}
</style></head><body>
<h2>Doorbell Cam Tuner</h2>
<p class='hint'>Move a slider, the preview updates live. Hit Save when the picture looks right —
saved settings are used by the normal doorbell mode from then on.</p>
<img id='pv' src='/capture'>
<div class='row'><label>White balance</label><input type='checkbox' id='wb'></div>
<div class='row'><label>WB mode</label><select id='wbmode'>
<option value='0'>Auto</option><option value='1'>Sunny</option><option value='2'>Cloudy</option>
<option value='3'>Office</option><option value='4'>Home</option></select></div>
<div class='row'><label>Brightness</label><input type='range' id='bright' min='-2' max='2' step='1'><span class='val' id='bright_v'></span></div>
<div class='row'><label>Contrast</label><input type='range' id='contrast' min='-2' max='2' step='1'><span class='val' id='contrast_v'></span></div>
<div class='row'><label>Saturation</label><input type='range' id='sat' min='-2' max='2' step='1'><span class='val' id='sat_v'></span></div>
<div class='row'><label>Auto exposure</label><input type='checkbox' id='aec'></div>
<div class='row'><label>Exposure (manual)</label><input type='range' id='aecval' min='0' max='1200' step='10'><span class='val' id='aecval_v'></span></div>
<div class='row'><label>Auto gain</label><input type='checkbox' id='agc'></div>
<div class='row'><label>Gain (manual)</label><input type='range' id='gain' min='0' max='30' step='1'><span class='val' id='gain_v'></span></div>
<div class='row'><label>Lens correction</label><input type='checkbox' id='lenc'></div>
<button onclick="fetch('/save').then(r=>r.text()).then(t=>alert(t))">Save settings</button>
<p class='hint'>Manual exposure/gain sliders only take effect when their Auto checkbox is off.</p>
<script>
const vars=['wb','wbmode','bright','contrast','sat','aec','aecval','agc','gain','lenc'];
function showVal(v){const s=document.getElementById(v+'_v');if(s){const el=document.getElementById(v);s.textContent=el.value;}}
fetch('/status').then(r=>r.json()).then(j=>{
  vars.forEach(v=>{const el=document.getElementById(v);if(!el)return;
    if(el.type=='checkbox')el.checked=!!j[v];else{el.value=j[v];showVal(v);}});
});
vars.forEach(v=>{const el=document.getElementById(v);if(!el)return;
  el.onchange=()=>{const val=el.type=='checkbox'?(el.checked?1:0):el.value;
    showVal(v);fetch('/control?var='+v+'&val='+val);};});
setInterval(()=>{document.getElementById('pv').src='/capture?t='+Date.now();},1200);
</script></body></html>
)rawliteral";

static void tunerApplyVar(const String &var, int val) {
  if (var == "wb") tune.wb = val ? 1 : 0;
  else if (var == "wbmode") tune.wbmode = constrain(val, 0, 4);
  else if (var == "bright") tune.bright = constrain(val, -2, 2);
  else if (var == "contrast") tune.contrast = constrain(val, -2, 2);
  else if (var == "sat") tune.sat = constrain(val, -2, 2);
  else if (var == "aec") tune.aec = val ? 1 : 0;
  else if (var == "aecval") tune.aecval = constrain(val, 0, 1200);
  else if (var == "agc") tune.agc = val ? 1 : 0;
  else if (var == "gain") tune.gain = constrain(val, 0, 30);
  else if (var == "lenc") tune.lenc = val ? 1 : 0;
  applyTune();
}

static void runTuner() {
  Serial.println("\n*** TUNER MODE ***");
  if (!init_camera()) {
    Serial.println("camera init failed");
    return;
  }
  if (!wifi_connect()) return;
  Serial.print("Tuner at http://");
  Serial.println(WiFi.localIP());

  tunerServer.on("/", HTTP_GET, []() {
    tunerServer.send_P(200, "text/html", TUNER_HTML);
  });
  tunerServer.on("/status", HTTP_GET, []() {
    char buf[160];
    snprintf(buf, sizeof(buf),
      "{\"wb\":%d,\"wbmode\":%d,\"bright\":%d,\"contrast\":%d,\"sat\":%d,"
      "\"aec\":%d,\"aecval\":%d,\"agc\":%d,\"gain\":%d,\"lenc\":%d}",
      tune.wb, tune.wbmode, tune.bright, tune.contrast, tune.sat,
      tune.aec, tune.aecval, tune.agc, tune.gain, tune.lenc);
    tunerServer.send(200, "application/json", buf);
  });
  tunerServer.on("/control", HTTP_GET, []() {
    if (tunerServer.hasArg("var") && tunerServer.hasArg("val")) {
      tunerApplyVar(tunerServer.arg("var"), tunerServer.arg("val").toInt());
      tunerServer.send(200, "text/plain", "ok");
    } else {
      tunerServer.send(400, "text/plain", "missing var/val");
    }
  });
  tunerServer.on("/capture", HTTP_GET, []() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) { tunerServer.send(500, "text/plain", "capture failed"); return; }
    tunerServer.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
  });
  tunerServer.on("/save", HTTP_GET, []() {
    saveTune();
    tunerServer.send(200, "text/plain", "Settings saved. Reboot normally to use them.");
  });
  tunerServer.begin();
  Serial.println("tuner running, serving...");

  for (;;) tunerServer.handleClient();  // never returns
}

void setup() {
  Serial.begin(115200);
  delay(100);
  pinMode(FLASH_GPIO, OUTPUT);
  digitalWrite(FLASH_GPIO, LOW);
  pinMode(PIR_GPIO, INPUT);

  loadTune();  // saved tuner settings, or defaults on first run

  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

  // Tuner mode: on a cold boot (power-on / RST press, not a PIR wake),
  // any key in the serial monitor within 8 s starts the web tuner.
  // PIR wakes skip the wait and go straight to capture.
  if (cause == ESP_SLEEP_WAKEUP_UNDEFINED) {
    Serial.println("Send any key within 8 s for TUNER mode...");
    unsigned long t0 = millis();
    while (millis() - t0 < 8000) {
      if (Serial.available()) {
        while (Serial.available()) Serial.read();
        runTuner();  // never returns
      }
      delay(50);
    }
  }

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
  }
  go_to_sleep();
}

void loop() { /* never reached in doorbell mode; tuner mode never returns */ }
