# BLE provisioning protocol

The setup app is the **JakinsCraft ESP Cam Setup** PWA (Chrome on Android,
Web Bluetooth): https://pappyakins.github.io/esp-cam-setup/ — source:
Pappyakins/esp-cam-setup. The protocol below is what it speaks.

How the JakinsCraft ESP Setup app configures a doorbell cam over
Bluetooth Low Energy. Implemented in `doorbell-cam.ino`; settings are
stored in the NVS namespace `doorcfg` and override `config.h`.

## When the camera listens

Provisioning starts only when ALL of these are true:

- the boot is a manual power-on (not a PIR wake),
- sending the power-on photo failed (Wi-Fi could not connect),
- fewer than 2 provisioning attempts since the last successful Wi-Fi
  connection (RTC counter, so a dead router cannot drain the battery).

It advertises for 5 minutes, blinking the flash LED once a second,
then gives up and goes back to deep sleep. A save or erase from the
app restarts the camera immediately.

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
