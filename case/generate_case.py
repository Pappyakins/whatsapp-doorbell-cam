#!/usr/bin/env python3
"""Generate STL files for the WhatsApp Doorbell Cam enclosure — pebble style.

v2 (2026-10-02): rebuilt with manifold3d CSG booleans. The v1 script glued
overlapping triangle soup together, which produced non-manifold meshes that
Bambu Studio refused to open. These outputs are true watertight solids.

Design (all mm):
  - Rounded-rectangle "pebble" body, 96 x 70 x 34.5, 2.5 wall, corner r12.
  - Front face with two flush circular bezels:
      * PIR bezel: outer r17, 23 mm bore (Pappy's spec, 2026-10-21 —
        line-to-line with the 23 mm HC-SR501 Fresnel dome, a snug grip)
      * Camera bezel: outer r10, 8 mm bore for the lens barrel, plus a
        separate 8 mm bore for the flash LED at (61.3, 33.1). The board
        mounts UPRIGHT, antenna at the TOP, never on its side (Pappy's
        checks against his own board, 2026-10-21): on his board the LED
        centre sits 8.7 mm LEFT and 20.9 mm below the lens centre
        (fine-tuned v3.10 from the first printed case).
        The camera sits high on the face (centre y=54) so the upright
        board's bottom end clears the battery bay — at y=41 it would
        foul the cell's shoulder.
  - Charger USB notch in the bottom wall (x 66..78, z 26..31, deep —
    beside the lid, where the TP4056 now stands; see v3.7 below).
  - 4x corner bosses (8 mm) take M3 brass heat-set inserts
    (4.1 mm blind hole, 7 mm deep, lead-in chamfer); use M3x8 screws.
  - Lid: matching rounded back plate, 5 mm, M3 clearance holes with
    socket-head counterbores on the outer face + 2x 5 mm mount holes.

Coordinates: x 0..96 (width), y 0..70 (height), z 0 at the body's front
outer surface, increasing toward the back opening (z=34.5). The lid STL is
exported in its own frame (z 0..3) so it drops flat onto the build plate.

Print: body FRONT-FACE-DOWN, lid flat. No supports. PETG recommended.
(The front face is fully flat — bezel rings are flush, so the first layer
sits completely on the build plate with no bridging.)

v3 (2026-10-06): battery edition. Adds an 18650 bay in the bottom of the
interior: two saddle ribs cradle the cell (axis along X, centred y=14),
end stops fit 65-68 mm cells (bare or protected flat-top). A zip tie locks
the cell in: it threads up through one floor slot, over the cell, down
through the other slot, and the buckle cinches into a shallow groove on
the outer face. Small boards (TP4056, boost) tape down beside the
cradle — standard DIY practice.

v3.1 (2026-10-08): bezel rings sunk flush with the front face so the body
prints front-face-down with the first layer fully on the build plate —
no bridging, no supports. Added the two zip-tie slots (the v3 groove had
no way to thread the tie through).

v3.3 (2026-10-08): PIR/camera bores raised 3 mm for ESP32-CAM clearance;
screw bosses converted to M3 brass heat-set inserts (8 mm boss, 4.1 mm
blind hole with lead-in chamfer).
v3.4 (2026-10-08): lid thickened to 5 mm with 5.6 mm dia socket-head
counterbores (3.2 deep) on the outer face — M3 socket-head screws sit
flush so the lid mounts flat to the wall.
v3.5 (2026-10-17): PIR bore reduced 26 -> 24 mm, snug fit for the 23 mm
HC-SR501 dome (the 26 mm bore was loose).
v3.6 (2026-10-18): camera bore 20 -> 12 mm (lens only, the big round hole
was oversized); bezel r14 -> r10; added a separate 8 mm flash LED bore
at (81, 27) — 13 mm right, 14 mm below the lens centre.

v3.7 (2026-10-20): full fit audit against the STANDARD part dimensions
(Ai-Thinker datasheet + published module sizes), checked pairwise for
interference by case/check_fit.py — run it after any layout change.
  - Flash bore MOVED to (51.8, 29.7). The v3.6 spot came from a photo
    measurement that does not match the standard board: measured on
    Ai-Thinker's own front photo and an assembled-board photo, the LED
    centre is 11.3 right / 18.2 below the lens in board coordinates, so
    with the board landscape (antenna end right, as ASSEMBLY.md says)
    the LED lands down-left of the lens. At the old spot the LED sat
    fully behind solid plastic in that mounting.
  - Camera centre moved (68, 41) -> (70, 41) so the ESP32-CAM PCB
    (40.5 long) clears the HC-SR501 PCB (32.5 wide) by 3+ mm.
  - Camera bore 12 -> 13 mm so the OV2640 lens base (9x9, corner
    radius 6.4) clears the bore rim.
  - Power boards get a defined home: TP4056 and MT3608 stand upright
    at the BACK of the case along the bottom wall (behind the battery),
    cap lying beside them — the old "tape beside the cradle" left no
    interference-free spot, and the charger notch could never reach
    the TP4056 with the cell in place. The front USB notch (x 41..55,
    blocked by the battery since v3) is removed; the charger notch
    moves deep (z 26..31) to meet the TP4056's USB port.

v3.8 (2026-10-21): Pappy's corrections, checked against his own board.
  - Board mounting is UPRIGHT (antenna top), not landscape: the flash
    LED sits right of the lens and below it, so the flash bore moves
    (51.8, 29.7) -> (81.3, 35.8). Camera centre (70, 41) -> (70, 54)
    so the upright board's bottom end (29 mm below the lens) clears
    the battery bay.
  - Camera bore 13 -> 8 mm (same as the flash bore; the 9x9 lens base
    now seats flat against the plate and only the barrel enters).
  - PIR bore 24 -> 23 mm (his spec: line-to-line with the dome).

v3.9 (2026-10-21): Pappy corrected the flash side once more, board in
  hand: the flash is to the LEFT of the lens (not the right as the
  stock photos suggested — his physical board wins). Flash bore
  (81.3, 35.8) -> (58.7, 35.8). Board stays upright, antenna up;
  camera stays at (70, 54).

v3.10 (2026-10-21): first printed case test-fitted. The flash LED sat
  off-centre in its bore; measured from Pappy's photo of the printed
  case, the LED centre is 1.1 mm further left and 0.7 mm lower than
  the stock-photo dimensions put it. Flash bore (58.7, 35.8) ->
  (59.8, 35.1), i.e. 10.2 LEFT / 18.9 below the lens on his board.
  Everything else unchanged.

v3.11 (2026-10-21): Pappy's own call from the printed case in hand,
  applied ON TOP of v3.10: flash bore 2.0 mm further down (away from
  the camera hole) and 1.5 mm towards the camera centre. Flash bore
  (59.8, 35.1) -> (61.3, 33.1), i.e. 8.7 LEFT / 20.9 below the lens.

Run with the project venv:
  ../.venv/bin/python generate_case.py
Outputs: doorbell-cam-body.stl, doorbell-cam-lid.stl (binary STL, mm).
"""
import os
import struct

import numpy as np
from manifold3d import CrossSection, Manifold, set_circular_segments

BASE = os.path.dirname(os.path.abspath(__file__))
set_circular_segments(96)

# ---------------------------------------------------------------- dims ---
CX, CY = 48.0, 35.0                    # case centre
W, H, R = 96.0, 70.0, 12.0             # outer silhouette
WI, HI, RI = 91.0, 65.0, 9.5           # inner cavity (2.5 wall)
T, D = 2.5, 34.5                       # front plate thickness, body depth
PIR = (24.0, 41.0)                     # PIR bezel centre (raised 3 mm for cam clearance)
CAM = (70.0, 54.0)                     # camera bezel centre (high on the face: the upright
                                       # board's bottom end must clear the battery bay)
FLASH = (61.3, 33.1)                   # flash LED bore centre: 8.7 LEFT, 20.9 below the
                                       # lens, board upright, antenna at the top
                                       # (Pappy's own board check, 2026-10-21)
BOSS = [(8, 8), (88, 8), (8, 62), (88, 62)]
MOUNT = [(48, 12), (48, 58)]           # lid wall-mount holes


def rounded_prism(w, h, r, z0, depth):
    """Rounded-rectangle prism centred on (CX, CY), from z0 up depth."""
    cs = CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r)
    return cs.extrude(depth).translate([CX, CY, z0])


def cyl(r, x, y, z0, depth):
    return Manifold.cylinder(depth, r, circular_segments=96).translate([x, y, z0])


def cyl_x(r, x0, y, z, length):
    """Cylinder with axis along X, spanning x0..x0+length, centred at (y, z)."""
    return (Manifold.cylinder(length, r, circular_segments=96)
            .rotate([0, 90, 0]).translate([x0, y, z]))


def box(x, y, z, sx, sy, sz):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])


def write_stl(solid, path):
    mesh = solid.to_mesh()
    verts = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    tris = np.asarray(mesh.tri_verts, dtype=np.int64)
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p, q, s = verts[a], verts[b], verts[c]
            n = np.cross(q - p, s - p)
            ln = np.linalg.norm(n)
            n = n / ln if ln > 0 else n
            f.write(struct.pack(
                "<12f", n[0], n[1], n[2],
                p[0], p[1], p[2], q[0], q[1], q[2], s[0], s[1], s[2]))
            f.write(struct.pack("<H", 0))
    print("wrote", path, len(tris), "triangles,",
          "volume %.0f mm^3" % solid.volume())


# ================================================================= body ==
def build_body():
    body = rounded_prism(W, H, R, 0.0, D)                    # outer shell
    body -= rounded_prism(WI, HI, RI, T, D)                  # hollow interior
    body += cyl(17.0, *PIR, 0.0, T)                           # PIR bezel ring (flush)
    body += cyl(10.0, *CAM, 0.0, T)                           # camera bezel ring (flush)
    for bx, by in BOSS:                                      # screw bosses (8 mm, insert-ready)
        body += cyl(4.0, bx, by, T, 31.5)
    body -= cyl(11.5, *PIR, -T - 1, 10.0)                    # PIR bore (23 mm, line-to-line with the dome)
    body -= cyl(4.0, *CAM, -T - 1, 10.0)                     # camera bore (8 mm, lens barrel; base seats on the plate)
    body -= cyl(4.0, *FLASH, -T - 1, 10.0)                   # flash LED bore (8 mm)
    for bx, by in BOSS:                                      # M3 insert holes (4.1, blind)
        body -= cyl(2.05, bx, by, 27.0, 8.0)
        body -= Manifold.cylinder(1.5, 2.05, 2.6, circular_segments=96).translate([bx, by, 33.0])  # lead-in funnel
    body -= box(66.0, -1.0, 26.0, 12.0, T + 1.5, 5.0)         # charger USB notch, bottom wall, deep (z 26..31) — meets the TP4056 standing at the back
    body -= box(45.5, 4.0, 0.0, 5.0, 20.0, 2.0)              # zip-tie groove, outer face
    body -= box(46.0, 3.0, 0.0, 4.0, 4.0, T)                # zip-tie slot, -Y side
    body -= box(46.0, 21.0, 0.0, 4.0, 4.0, T)               # zip-tie slot, +Y side
    # --- 18650 battery bay (cell axis along X at y=14, z-centre 12, r9) ---
    for sx in (24.0, 56.0):                                 # saddle ribs
        saddle = box(sx, 4.0, T, 6.0, 20.0, 18.5)
        saddle -= cyl_x(9.5, sx - 2.0, 14.0, 12.0, 10.0)     # cradle cutout
        body += saddle
    body += box(12.0, 6.0, T, 2.0, 16.0, 15.5)               # end stop, -X
    body += box(82.0, 6.0, T, 2.0, 16.0, 15.5)               # end stop, +X
    return body


# ================================================================== lid ==
LID_T = 5.0                              # lid thickness (fits M3 socket-head counterbore)

def build_lid():
    lid = rounded_prism(W, H, R, 0.0, LID_T)
    for bx, by in BOSS:                                      # M3 clearance (3.4)
        lid -= cyl(1.7, bx, by, -1.0, LID_T + 2.0)
    for bx, by in BOSS:                  # socket-head counterbore (5.6 dia, 3.2 deep)
        lid -= cyl(2.8, bx, by, LID_T - 3.2, 4.0)   # outer face = z=LID_T side
    for mx, my in MOUNT:                                     # wall mount (5 mm)
        lid -= cyl(2.5, mx, my, -1.0, LID_T + 2.0)
    return lid


if __name__ == "__main__":
    write_stl(build_body(), os.path.join(BASE, "doorbell-cam-body.stl"))
    write_stl(build_lid(), os.path.join(BASE, "doorbell-cam-lid.stl"))
