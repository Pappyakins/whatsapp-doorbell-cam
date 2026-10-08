# Doorbell Cam — Assembly Instructions

## Parts checklist

| Qty | Part |
|---|---|
| 1 | Printed body (`doorbell-cam-body.stl`) |
| 1 | Printed lid (`doorbell-cam-lid.stl`) |
| 1 | ESP32-CAM (AI-Thinker, OV2640) |
| 1 | HC-SR501 PIR sensor |
| 1 | 18650 cell, flat-top, 65–68 mm (e.g. Samsung 30Q) |
| 1 | TP4056 charger board **with protection**, micro-USB port |
| 1 | 5V boost converter module |
| 1 | 470µF electrolytic capacitor |
| 4 | M3 brass heat-set inserts (≈4.6 mm OD × 5.7 mm long) |
| 4 | M3×10 socket-head screws (lid → body) |
| 2 | Wall screws + anchors (for the 5 mm lid holes — sized to your wall) |
| 1 | Small zip tie (≈2.5 mm wide) |
| — | Jumper wire, solder |
| — | VHB tape or hot glue (board mounting) |

Tools: 3D printer, soldering iron (also used for the inserts), FTDI USB-to-TTL
programmer (3.3V) for flashing, small Phillips screwdriver, flush cutters.

## 1. Print the case

- PETG recommended (porch, sun, heat). 0.2 mm layers, 3 walls, 15% infill.
- **Body: print front-face-down** (the flat face with the two round bores goes
  on the build plate). **Lid: print flat** (5 mm; the counterbore recesses
  are on the top face). No supports needed for either.

## 2. Install the brass inserts

- Heat your soldering iron to ~200°C (a dedicated insert tip helps, plain tip works).
- Press one M3 insert into each of the 4 corner boss holes, straight down
  until the top sits **flush** with the boss face. Let cool before touching.
- The holes have a small lead-in funnel — the insert should start easily by hand.

## 3. Flash the ESP32-CAM (do this before it goes in the case)

1. Copy `firmware/config.h.example` to `firmware/config.h`; fill in Wi-Fi,
   server URL, and device token.
2. FTDI → ESP32-CAM: 3.3V→3V3, GND→GND, TX→U0R, RX→U0T.
3. Hold **GPIO0 to GND**, press RST, upload the sketch, then release GPIO0.
4. Full flashing details: `firmware/README.md`.

## 4. Wire the power chain (on the bench)

```
18650 (+) → TP4056 B+      18650 (−) → TP4056 B−
TP4056 OUT+ → boost IN+     TP4056 OUT− → boost IN−
boost OUT+ (+5V) → ESP32-CAM 5V pin
boost OUT− (GND) → common ground
470µF capacitor across +5V / GND, as close to the ESP32-CAM as possible
```

- Double-check 18650 polarity before connecting — reverse polarity can kill
  the charger (the protection board is a backstop, not a plan).
- Common ground everywhere: battery −, TP4056, boost, ESP32-CAM, PIR.

## 5. Wire the PIR

| HC-SR501 | Goes to |
|---|---|
| VCC | +5V rail |
| GND | GND |
| OUT | ESP32-CAM **GPIO13** |

- PIR output is 3.3V logic — safe directly into GPIO13.
- Set the sensitivity/time pots to mid-range; put the jumper on **H**
  (retrigger mode).

## 6. Mount the boards in the body

- **ESP32-CAM:** behind the 20 mm bore, lens centred in the hole, **board
  long-side horizontal**. The flash LED sits beside the lens inside the same
  bore. Fix with VHB tape or a dab of hot glue — keep the ESP antenna area
  clear of metal.
- **PIR:** behind the 26 mm bore with the white Fresnel dome poking into it.
  Same fixing method.
- Keep the boards 2–3 mm off the front plate if you can; the bores were
  positioned so nothing fouls the battery bay.

## 7. Fit the battery

1. Lay the 18650 in the saddle cradle (axis along X, between the end stops).
2. Feed the zip tie **up through one floor slot** (from the outside), **over
   the cell**, and **down through the other slot**.
3. Cinch it so the buckle seats in the shallow groove on the outer face.
   Snug, not crushing. Trim the tail.

## 8. Fit the charger and boost boards

- Tape the TP4056 and boost module down **beside** the cradle with VHB tape.
- Line the TP4056's USB port up with the charger notch in the bottom wall —
  that's how you'll plug in to recharge without opening the case.

## 9. Bench-test before closing

1. Power up, wave a hand in front of the PIR.
2. You should get a WhatsApp photo captioned "🔔 Someone's at the door!".
3. If nothing arrives: check the server endpoint is up, the token matches,
   and the PIR OUT line actually goes high (multimeter on GPIO13).

## 10. Mount it

1. Hold the **lid** against the door frame/wall at ~1.5 m height, beside the
   door, aimed down the walkway — away from direct sun and HVAC vents.
2. Fix the lid with 2 screws through the 5 mm holes (**screw heads inside**).
3. Offer the body up and close it with the 4× M3×10 screws into the inserts —
   heads sit flush in the lid counterbores (recesses face outward, away
   from the body). Don't overtighten — snug is enough in PETG.

## Recharging

Plug a USB cable into the TP4056 port through the charger notch. The charger's
onboard LED shows charging/full. A 3000 mAh cell lasts roughly 3–4 weeks on a
stock board (less with heavy foot traffic); the regulator-bypass mod in the
main README stretches that to months.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Photo never arrives | Token mismatch, server endpoint down, or no Wi-Fi at the door |
| Board resets when snapping | Missing/weak 5V — check the 470µF cap and boost output under load |
| Constant false triggers | PIR facing sun/vent, sensitivity pot too high |
| Insert spins in boss | Hole printed oversize — a drop of CA glue around the insert saves it |
| Case won't close on lid | Check nothing (boost board, wires) stands taller than the bosses |

---
Powered by @jakinsCraft
