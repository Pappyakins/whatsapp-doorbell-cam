#!/usr/bin/env python3
"""Interference check for the doorbell cam enclosure (v3.7 layout).

Every part is modelled as a conservative box (x0,x1, y0,y1, z0,z1) in case
coordinates: x 0..96 left-to-right across the front face, y 0..70 bottom
to top, z 0 at the front outer surface increasing toward the lid (34.5).

Part sizes are the STANDARD published dimensions:
  ESP32-CAM (Ai-Thinker datasheet)  40.5 x 27 x 4.5 mm
    lens centre 13.5 across, 11.5 down from the board's top edge
    flash LED centre 24.8 across, 29.8 down (measured on the official
    Ai-Thinker front photo and an assembled-board photo, Oct 2026)
    -> on the stock board the LED measures 11.3 right / 18.2 below the
    lens, but on PAPPY'S board it sits to the LEFT (his check against
    the physical board, 2026-10-21 — his board wins). Board mounted
    UPRIGHT, antenna at the TOP, so in case coordinates the LED is
    11.2 LEFT / 20.9 BELOW the lens (fine-tuned v3.10/v3.11: LED centre
    measured off-centre in the first printed case, 2026-10-21).
    Camera centre (70, 54): the
    upright board's bottom end reaches 29 mm below the lens and must
    clear the battery bay.
  HC-SR501 PIR                      PCB 32.5 x 24.5, dome dia 23, ~10 tall
  TP4056 module (protected, uUSB)   ~26 x 17.5 (clones vary +/-2)
  MT3608 boost module               ~36 x 17 (clones vary +/-1)
  18650 cell                        dia 18.8 worst case, 65-68 long
  470uF capacitor                   dia 8 x 10 long (typical)

Run: ../.venv/bin/python check_fit.py   (exit 1 if any clash is found)
"""
import itertools
import sys

# name -> (x0, x1, y0, y1, z0, z1)
PARTS = {
    # --- PIR, dome seated in its bore, PCB ~10 mm behind the front face
    "pir_pcb":      (7.75, 40.25, 28.75, 53.25, 10.0, 11.6),
    "pir_pot_L":    (11.0, 16.0, 48.0, 53.0, 11.6, 16.6),
    "pir_pot_R":    (32.0, 37.0, 48.0, 53.0, 11.6, 16.6),
    "pir_header":   (21.0, 27.0, 29.0, 32.0, 11.6, 14.0),
    # --- ESP32-CAM, upright, antenna at the top, lens at (70, 54)
    "esp_pcb":      (56.5, 83.5, 25.0, 65.5, 4.5, 6.1),
    "esp_shield":   (61.0, 79.0, 33.5, 53.5, 6.1, 9.5),   # ESP32 can, back side
    "esp_pins_L":   (56.8, 58.8, 28.5, 60.5, 6.1, 14.5),  # worst case: headers
    "esp_pins_R":   (81.2, 83.2, 28.5, 60.5, 6.1, 14.5),  #   soldered both rows
    "esp_led":      (56.6, 61.0, 30.9, 35.3, 3.5, 4.5),   # flash LED, front face (left of lens)
    # --- 18650 in its bay (intentional contact with saddles/stops excluded)
    "battery":      (14.0, 82.0, 4.6, 23.4, 2.6, 21.4),
    # --- power boards standing at the back, bottom zone, faces toward cell
    "tp4056":       (64.0, 83.0, 3.0, 29.0, 25.0, 30.0),  # incl. USB socket
    "boost":        (15.5, 52.5, 3.0, 20.0, 23.0, 30.2),  # incl. inductor/pot
    "cap_470uF":    (53.0, 63.0, 2.5, 10.5, 22.5, 30.5),  # lying on bottom wall
    # --- case features the parts must clear
    "boss_BL":      (4.0, 12.0, 4.0, 12.0, 2.5, 34.0),
    "boss_BR":      (84.0, 92.0, 4.0, 12.0, 2.5, 34.0),
    "boss_TL":      (4.0, 12.0, 58.0, 66.0, 2.5, 34.0),
    "boss_TR":      (84.0, 92.0, 58.0, 66.0, 2.5, 34.0),
    "endstop_L":    (12.0, 14.0, 6.0, 22.0, 2.5, 18.0),
    "endstop_R":    (82.0, 84.0, 6.0, 22.0, 2.5, 18.0),
    "saddle_L":     (24.0, 30.0, 4.0, 24.0, 2.5, 21.0),
    "saddle_R":     (56.0, 62.0, 4.0, 24.0, 2.5, 21.0),
    "mount_head_B": (43.5, 52.5, 7.5, 16.5, 32.0, 34.5),  # wall screw heads
    "mount_head_T": (43.5, 52.5, 53.5, 62.5, 32.0, 34.5),  #   inside the case
}

# pairs that touch by design (the cell is cradled by the saddles/stops)
INTENTIONAL = {
    frozenset(("battery", "saddle_L")), frozenset(("battery", "saddle_R")),
    frozenset(("battery", "endstop_L")), frozenset(("battery", "endstop_R")),
}

CAVITY = (2.5, 93.5, 2.5, 67.5, 2.5, 34.5)  # parts must stay inside


def overlaps(a, b):
    return all(a[i] < b[i + 1] and b[i] < a[i + 1] for i in (0, 2, 4))


def main():
    bad = 0
    for name, p in PARTS.items():
        if any(p[i] < CAVITY[i] or p[i + 1] > CAVITY[i + 1] for i in (0, 2, 4)):
            print(f"OUTSIDE CAVITY: {name} {p}")
            bad += 1
    for (na, a), (nb, b) in itertools.combinations(sorted(PARTS.items()), 2):
        if frozenset((na, nb)) in INTENTIONAL:
            continue
        if overlaps(a, b):
            print(f"CLASH: {na} {a}  x  {nb} {b}")
            bad += 1
    # flash LED must sit fully inside the flash bore footprint (58.8, 33.1) r4
    led = PARTS["esp_led"]
    cx, cy, r = 58.8, 33.1, 4.0
    if not (led[0] >= cx - r and led[1] <= cx + r
            and led[2] >= cy - r and led[3] <= cy + r):
        print("FLASH: LED footprint not fully inside the bore")
        bad += 1
    print("check_fit:", "FAIL" if bad else "all parts clear, no interference")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
