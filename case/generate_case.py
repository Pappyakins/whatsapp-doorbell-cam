#!/usr/bin/env python3
"""Generate STL files for the WhatsApp Doorbell Cam enclosure — pebble style.

v2 (2026-10-02): rebuilt with manifold3d CSG booleans. The v1 script glued
overlapping triangle soup together, which produced non-manifold meshes that
Bambu Studio refused to open. These outputs are true watertight solids.

Design (all mm):
  - Rounded-rectangle "pebble" body, 96 x 70 x 34.5, 2.5 wall, corner r12.
  - Front face with two raised circular bezels (2.5 proud):
      * PIR bezel: outer r17, 26 mm bore for the HC-SR501 Fresnel dome (23 mm)
      * Camera bezel: outer r14, 20 mm bore covering lens + flash LED
  - USB cable notch in the bottom wall (x 41..55, 5.5 tall, behind front plate).
  - 4x corner bosses take M3 self-tapping screws (2.8 mm pilot).
  - Lid: matching rounded back plate, 3 mm, M3 clearance + 2x 5 mm mount holes.

Coordinates: x 0..96 (width), y 0..70 (height), z 0 at the body's front
outer surface, increasing toward the back opening (z=34.5). The lid STL is
exported in its own frame (z 0..3) so it drops flat onto the build plate.

Print: body FRONT-FACE-DOWN, lid flat. No supports. PETG recommended.
(The front face is fully flat — bezel rings are flush, so the first layer
sits completely on the build plate with no bridging.)

v3 (2026-10-06): battery edition. Adds an 18650 bay in the bottom of the
interior: two saddle ribs cradle the cell (axis along X, centred y=14),
end stops fit 65-68 mm cells (bare or protected flat-top), a zip-tie
groove in the floor under the cell mid-point, and a second USB notch in
the bottom wall for the TP4056 charger's USB port. Small boards
(TP4056, boost) tape down beside the cradle — standard DIY practice.

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
PIR = (24.0, 38.0)                     # PIR bezel centre
CAM = (68.0, 38.0)                     # camera bezel centre
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
    body += cyl(14.0, *CAM, 0.0, T)                           # camera bezel ring (flush)
    for bx, by in BOSS:                                      # screw bosses
        body += cyl(3.5, bx, by, T, 31.5)
    body -= cyl(13.0, *PIR, -T - 1, 10.0)                    # PIR bore (26 mm)
    body -= cyl(10.0, *CAM, -T - 1, 10.0)                    # camera bore (20 mm)
    for bx, by in BOSS:                                      # M3 pilot holes (2.8)
        body -= cyl(1.4, bx, by, T, 33.0)
    body -= box(41.0, -1.0, T, 14.0, T + 1.5, 5.5)           # USB notch, bottom wall
    body -= box(66.0, -1.0, T, 12.0, T + 1.5, 5.5)           # charger USB notch
    body -= box(45.5, 4.0, 0.0, 5.0, 20.0, 2.0)              # zip-tie groove, floor
    # --- 18650 battery bay (cell axis along X at y=14, z-centre 12, r9) ---
    for sx in (24.0, 56.0):                                 # saddle ribs
        saddle = box(sx, 4.0, T, 6.0, 20.0, 18.5)
        saddle -= cyl_x(9.5, sx - 2.0, 14.0, 12.0, 10.0)     # cradle cutout
        body += saddle
    body += box(12.0, 6.0, T, 2.0, 16.0, 15.5)               # end stop, -X
    body += box(82.0, 6.0, T, 2.0, 16.0, 15.5)               # end stop, +X
    return body


# ================================================================== lid ==
def build_lid():
    lid = rounded_prism(W, H, R, 0.0, 3.0)
    for bx, by in BOSS:                                      # M3 clearance (3.4)
        lid -= cyl(1.7, bx, by, -1.0, 5.0)
    for mx, my in MOUNT:                                     # wall mount (5 mm)
        lid -= cyl(2.5, mx, my, -1.0, 5.0)
    return lid


if __name__ == "__main__":
    write_stl(build_body(), os.path.join(BASE, "doorbell-cam-body.stl"))
    write_stl(build_lid(), os.path.join(BASE, "doorbell-cam-lid.stl"))
