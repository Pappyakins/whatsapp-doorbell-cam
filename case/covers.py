#!/usr/bin/env python3
"""Printable covers for the WhatsApp Doorbell Cam case (v3.13 face).

1. flash-diffuser.stl - a clear-PETG cap for the 12 mm flash bore at
   (58.8, 35.1). A 16 mm flange sits on the front face (glue dabs or UV
   resin on the rim) and an 11.7 mm stem presses into the bore. Printed
   in clear PETG at 100% infill it frosts the LED light and spreads it,
   which also hides the LED sitting off-centre in the bore.

2. ziptie-cover.stl - a flush plug for the zip-tie groove on the front
   face (x 45.5..50.5, y 4..24, 2 mm deep). Capsule 4.95 x 19.95 x 2 mm
   with two 3.6 mm pegs that drop into the 4 mm tie slots (slot centres
   y=5 and y=23) so it locates and cannot slide. For tie-free builds;
   if the battery zip tie is fitted, its buckle lives in this groove
   instead and the cover is not used.

Both parts print face-down as exported (z=0 is the visible outer face),
no supports. Run with the project venv: ../.venv/bin/python covers.py
"""
import os
import struct

import numpy as np
from manifold3d import CrossSection, Manifold, set_circular_segments

BASE = os.path.dirname(os.path.abspath(__file__))
set_circular_segments(96)


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


def flash_diffuser():
    flange = Manifold.cylinder(1.2, 8.0, circular_segments=96)          # Ø16 x 1.2
    stem = Manifold.cylinder(2.3, 5.85, circular_segments=96) \
        .translate([0, 0, 1.2])                                          # Ø11.7 x 2.3
    return flange + stem


def ziptie_cover():
    r = 4.95 / 2.0
    cs = CrossSection.square([4.95 - 2 * r, 19.95 - 2 * r],
                             center=True).offset(r)                     # capsule plan
    plug = cs.extrude(2.0)                                              # 2 mm = groove depth
    for dy in (-9.0, 9.0):                                              # slot centres, plug frame
        plug += Manifold.cube([3.6, 3.6, 1.5]).translate([-1.8, dy - 1.8, 2.0])
    return plug


if __name__ == "__main__":
    write_stl(flash_diffuser(), os.path.join(BASE, "flash-diffuser.stl"))
    write_stl(ziptie_cover(), os.path.join(BASE, "ziptie-cover.stl"))
