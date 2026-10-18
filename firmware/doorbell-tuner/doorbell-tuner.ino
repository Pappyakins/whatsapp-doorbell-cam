// Doorbell Cam Tuner — standalone bench tool (NOT the doorbell firmware).
//
// Flash this temporarily to dial in the camera picture. It connects to
// WiFi and serves a web page with a live preview plus sliders for every
// image setting (white balance, WB mode, brightness, contrast, saturation,
// exposure, gain, lens correction). Move a slider, the preview updates.
// Hit Save and the values are stored in the board's flash.
//
// Workflow:
//   1. Copy config.h from the ../firmware folder into THIS folder
//      (the tuner needs your WiFi credentials; config.h is gitignored).
//   2. Flash this sketch, open Serial Monitor at 115200, note the IP.
//   3. Open the IP in a browser, dial in the picture, hit Save.
//   4. Re-flash ../firmware/doorbell-cam.ino — it reads the saved values.
//
// If the camera fails to init here, the real problem is hardware/IDE
// settings (see README), not the doorbell firmware.

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
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
static WebServer tunerServer(80);

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
  cfg.frame_size = FRAMESIZE_SVGA;
  cfg.jpeg_quality = 10;
  cfg.fb_count = 1;
  cfg.fb_location = CAMERA_FB_IN_PSRAM;
  cfg.grab_mode = CAMERA_GRAB_LATEST;
  if (esp_camera_init(&cfg) != ESP_OK) return false;
  applyTune();
  return true;
}

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
.code{background:#222;padding:10px;font-family:monospace;font-size:13px;white-space:pre-wrap}
</style></head><body>
<h2>Doorbell Cam Tuner</h2>
<p class='hint'>Move a slider, the preview updates live. Hit Save when the picture looks right,
then re-flash the doorbell firmware which reads these saved values.</p>
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

static void halt(const char *msg) {
  Serial.println(msg);
  Serial.println("HALTED - check the README troubleshooting section.");
  for (;;) delay(1000);
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n*** DOORBELL CAM TUNER ***");

  loadTune();

  if (!init_camera()) halt("camera init failed");

  Serial.print("Connecting WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 12000) {
    delay(250);
    Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) halt("wifi failed");
  Serial.print("\nTuner at http://");
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
    tunerServer.send(200, "text/plain", "Settings saved. Re-flash doorbell-cam.ino to use them.");
  });
  tunerServer.begin();
  Serial.println("tuner running");
}

void loop() {
  tunerServer.handleClient();
}
