# BLE provisioning protocol

**Building the firmware:** install the **NimBLE-Arduino** library (by
h2zero) in the Arduino Library Manager first. The firmware uses NimBLE
instead of the built in Bluedroid BLE stack, and `send_photo()` writes
its HTTPS POST by hand instead of using HTTPClient — together those
two changes keep the build inside the ESP32 IRAM limit on core 3.3.12
(Bluedroid + HTTPClient overflowed `iram0_0_seg` by about 4 KB).

The setup app is the **JakinsCraft ESP Cam Setup** PWA (Chrome on Android,
Web Bluetooth): https://pappyakins.github.io/esp-cam-setup/ — source:
Pappyakins/esp-cam-setup. The protocol below is what it speaks.

How the JakinsCraft ESP Setup app configures a doorbell cam over
Bluetooth Low Energy. Implemented in `doorbell-cam.ino`; settings are
stored in the NVS namespace `doorcfg` and override `config.h`.

## When the camera listens

Provisioning starts on EVERY manual power-on boot (never on a PIR
wake). The setup window opens first, before the boot photo: it
advertises for 5 minutes, blinking the flash LED once a second. If
the app saves or erases settings, the camera restarts immediately
onto the new settings. If nobody connects in the 5 minutes, the cam
carries on with its normal boot photo and send, then sleeps.

Changed 2026-10-21 at Pappy's direction: entering setup must not
depend on Wi-Fi failing (the old rule also capped attempts at 2,
which made a working camera nearly impossible to reconfigure away
from home). A physical setup button is planned as a later addition
and will trigger this same window.

## Device identity

- Advertised name: `JakinsCam-XXXX` where XXXX is the last 4 hex
  digits of the Bluetooth MAC.
- Service UUID: `8d4f0001-3c2a-4b5e-9f1a-2b3c4d5e6f70`

## Characteristics (all under the service above)

| UUID | Field | Access | Notes |
| --- | --- | --- | --- |
| `8d4f0002-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Wi-Fi SSID | read/write | Pre-filled with the current SSID |
| `8d4f0003-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Wi-Fi password | write | Read returns empty; blank on APPLY keeps the stored password |
| `8d4f0004-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Camera name | read/write | e.g. `Front Door`; blank is allowed |
| `8d4f0005-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Receiver WhatsApp | read/write | Digits with country code; blank = server default. The server only honors numbers on its allowlist |
| `8d4f0006-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Server URL | read/write | Pre-filled |
| `8d4f0007-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Device token | read/write | Pre-filled |
| `8d4f0008-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Control / status | read/write | Write `APPLY` to save + restart, `ERASE` to wipe + restart. Read returns `ready`, `saved`, or `erased` |

All values are plain UTF-8 strings, no terminator. Writes are single
characteristic writes; keep each value under 200 bytes.

## App flow

1. Scan for the service UUID, connect to the `JakinsCam-XXXX` device.
2. Read SSID, name, receiver, server, token to pre-fill the form.
3. Let the user edit, then write back every field (password too;
   leave it blank to keep the stored one).
4. Write `APPLY` to the control characteristic, then read it back:
   `saved` means the camera stored the settings and is restarting.
5. Success on the camera side looks like the usual "doorbell online"
   photo arriving on WhatsApp once it joins the new Wi-Fi.
