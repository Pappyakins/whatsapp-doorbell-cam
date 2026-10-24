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
wake), UNLESS the setup is locked (see below). The setup window
opens first, before the boot photo: it advertises for 2 minutes,
blinking the flash LED once a second. If the app saves or erases
settings, the camera restarts immediately onto the new settings. If
nobody connects in the 2 minutes, the cam carries on with its normal
boot photo and send, then sleeps.

Changed 2026-10-21 at Pappy's direction: entering setup must not
depend on Wi-Fi failing (the old rule also capped attempts at 2,
which made a working camera nearly impossible to reconfigure away
from home).

## Locking the setup

The app can write `LOCK` to the control characteristic instead of
`APPLY`. That saves the settings AND sets a `locked` flag in NVS.
On later power-on boots a locked cam skips the setup window entirely
and goes straight to the boot photo, so it stops asking for details
every boot. `ERASE` wipes the whole `doorcfg` namespace, lock
included, so an erased cam is unlocked again.

The flag only changes through the app's lock slider: `LOCK` sets it,
`UNLOCK` clears it without restarting the cam. If the setup window
times out with no action, the flag stays exactly as it was. A
dedicated read-only characteristic reports the flag (`locked` /
`unlocked`) so the app can position its slider on connect: slider on
means locked, slider off means unlocked.

## Setup button (the way back in)

A locked cam never advertises, so the app cannot reach it on an
ordinary boot. The way back in is a physical button: one side to
GPIO 14, the other side to GND. The firmware configures GPIO 14 as
INPUT_PULLUP and samples it at power-on, so the button is active LOW.
Hold the button while powering the cam on and keep holding it until
the flash starts blinking: the cam opens the setup window as normal.
Holding the button does NOT clear the lock, so after that session the
cam is still locked until the slider is moved to off. If the button
is not held, a locked cam boots straight to its photo. The button
does nothing on a PIR wake.

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
| `8d4f0008-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Control / status | read/write | Write `APPLY` to save + restart, `LOCK` to save + lock + restart, `UNLOCK` to clear the lock (no restart), `ERASE` to wipe + restart. Read returns `ready`, `saved`, `locked`, `unlocked`, or `erased` |
| `8d4f0009-3c2a-4b5e-9f1a-2b3c4d5e6f70` | Lock state | read | Returns `locked` or `unlocked`; the app positions its lock slider from this on connect |

All values are plain UTF-8 strings, no terminator. Writes are single
characteristic writes; keep each value under 200 bytes.

## App flow

1. Scan for the service UUID, connect to the `JakinsCam-XXXX` device.
2. Read SSID, name, receiver, server, token to pre-fill the form, and
   read the lock state to position the lock slider (on = locked).
3. Let the user edit, then write back every field (password too;
   leave it blank to keep the stored one).
4. Write `APPLY` to the control characteristic, then read it back:
   `saved` means the camera stored the settings and is restarting.
   Write `LOCK` instead and the camera also sets its locked flag:
   read back `locked`, and later power-on boots skip setup entirely
   until the setup button (GPIO 14 to GND) is held at power-on.
   Write `UNLOCK` to clear the flag without restarting; read back
   `unlocked`.
5. Success on the camera side looks like the usual "doorbell online"
   photo arriving on WhatsApp once it joins the new Wi-Fi.
