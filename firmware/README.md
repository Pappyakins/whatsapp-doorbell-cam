# Doorbell Cam firmware

Arduino sketch for the AI-Thinker ESP32-CAM. Deep-sleeps until the PIR
wakes it, snaps an 800x600 JPEG, POSTs it to the home server, blinks the
flash LED, and sleeps again.

## Tuner mode (dial in the picture yourself)

On a cold boot (power-on or RST press) the board waits 8 seconds for any
key in the serial monitor. Type a character and press Enter inside that
window and it starts a web tuner instead of the doorbell flow. The serial
monitor prints its address, e.g. `Tuner at http://192.168.2.xxx`. Open
that on your phone or laptop: you get a live preview plus sliders for
white balance, WB mode, brightness, contrast, saturation, exposure (auto
+ manual), gain (auto + manual) and lens correction. Move a slider and
the preview updates. Hit **Save settings** and the values are stored in
the board's flash — the normal doorbell flow uses them from then on.
Reboot without sending a key to go back to doorbell mode. (PIR wakes skip
the 8 s wait and go straight to capture.)

## Flashing

1. Install the Arduino IDE + ESP32 board support (esp32 by Espressif).
2. Board: **AI Thinker ESP32-CAM**. Partition scheme: default is fine.
3. Copy `config.h.example` to `config.h` and fill in your Wi-Fi details,
   the server URL, and the device token (Muse gives you the token —
   it must match `doorbell_token.txt` on the server).
4. Connect the FTDI programmer: 3.3V -> 3V3, GND -> GND, TX -> U0R,
   RX -> U0T. Hold **GPIO0 to GND** while pressing RST to enter
   download mode, then upload.
5. **Never commit `config.h`.** It is gitignored.

## Wiring

| ESP32-CAM | Other          |
|-----------|----------------|
| 5V        | Boost +5V out  |
| GND       | GND (common)   |
| GPIO13    | HC-SR501 OUT   |
| GPIO4     | (on-board flash LED) |

- HC-SR501 VCC -> 5V (it wants 4.5–12V), GND -> GND.
- HC-SR501 output is 3.3V logic — safe straight into GPIO13.
- Set the PIR sensitivity/time pots mid-range; the jumper on **H**
  (retrigger) is recommended.
- 18650 (+) -> TP4056 B+/B-, TP4056 OUT -> 5V boost in,
  boost out -> ESP32-CAM 5V. Common ground everywhere.

## Power

Deep sleep draws microamps; the board is awake only ~10–20 seconds per
visitor. A 3000mAh 18650 lasts roughly 1–3 months depending on foot
traffic. The printed case (v3+) has the battery bay, charger USB notch,
and zip-tie retainer groove.
