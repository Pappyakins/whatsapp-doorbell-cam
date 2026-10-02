#!/usr/bin/env python3
"""Generate STL files for the WhatsApp Doorbell Cam enclosure.

Design (all mm):
  - Body: 96 x 70 x 34.5 outer, 2.5 wall. Front panel carries a 26x26 window
    for the HC-SR501 Fresnel dome and a 16x26 slot for the ESP32-CAM lens
    (+ flash LED tolerance). USB cable slot in the bottom wall.
  - 4x corner bosses take M3 self-tapping screws (2.8mm pilot).
  - Lid: 96 x 70 x 3.5 with M3 clearance holes (counterbored flush on the
    back face) and 2x 5mm square holes to screw the lid to the wall first.

Print: body FRONT-FACE-DOWN (windows on the build plate), lid flat.
No supports needed. PETG recommended for porch/sun use.

Outputs: doorbell-cam-body.stl, doorbell-cam-lid.stl (binary STL, mm).
Only the Python standard library is used.
"""
import struct
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))

tris = []


def tri(a, b, c):
    tris.append((tuple(a), tuple(b), tuple(c)))


def box(x0, y0, z0, x1, y1, z1):
    """Axis-aligned box with outward-facing triangles."""
    # bottom (-z)
    tri((x0, y0, z0), (x1, y1, z0), (x1, y0, z0))
    tri((x0, y0, z0), (x0, y1, z0), (x1, y1, z0))
    # top (+z)
    tri((x0, y0, z1), (x1, y0, z1), (x1, y1, z1))
    tri((x0, y0, z1), (x1, y1, z1), (x0, y1, z1))
    # front (+y)
    tri((x0, y1, z0), (x1, y1, z1), (x1, y1, z0))
    tri((x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
    # back (-y)
    tri((x0, y0, z0), (x1, y0, z0), (x1, y0, z1))
    tri((x0, y0, z0), (x1, y0, z1), (x0, y0, z1))
    # right (+x)
    tri((x1, y0, z0), (x1, y1, z0), (x1, y1, z1))
    tri((x1, y0, z0), (x1, y1, z1), (x1, y0, z1))
    # left (-x)
    tri((x0, y0, z0), (x0, y1, z1), (x0, y1, z0))
    tri((x0, y0, z0), (x0, y0, z1), (x0, y1, z1))


def _ring(cx, cy, r, z, n):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]


def screw_boss(cx, cy, r_out, r_in, z0, z1, n=32):
    """Hollow cylindrical boss, open at the bottom (sits on a panel)."""
    outer0, outer1 = _ring(cx, cy, r_out, z0, n), _ring(cx, cy, r_out, z1, n)
    inner0, inner1 = _ring(cx, cy, r_in, z0, n), _ring(cx, cy, r_in, z1, n)
    for i in range(n):
        j = (i + 1) % n
        # outer wall (normal points outward)
        tri(outer0[i], outer0[j], outer1[j])
        tri(outer0[i], outer1[j], outer1[i])
        # inner hole wall (normal points toward the axis)
        tri(inner0[i], inner1[j], inner0[j])
        tri(inner0[i], inner1[i], inner1[j])
        # top annulus (normal +z)
        tri(outer1[i], outer1[j], inner1[j])
        tri(outer1[i], inner1[j], inner1[i])


def slab_boxes(x0, x1, y0, y1, z0, z1, holes):
    """Fill a thin XY slab with boxes, skipping rectangular holes.

    holes: list of (hx0, hx1, hy0, hy1)."""
    ys = sorted(set([y0, y1] + [h[2] for h in holes] + [h[3] for h in holes]))
    for ya, yb in zip(ys, ys[1:]):
        ya, yb = max(ya, y0), min(yb, y1)
        if yb <= ya:
            continue
        ohs = [h for h in holes if h[2] < yb and h[3] > ya]
        xs = sorted(set([x0, x1] + [h[0] for h in ohs] + [h[1] for h in ohs]))
        for xa, xb in zip(xs, xs[1:]):
            xa, xb = max(xa, x0), min(xb, x1)
            if xb <= xa:
                continue
            if any(h[0] <= xa and h[1] >= xb for h in ohs):
                continue  # inside a hole
            box(xa, ya, z0, xb, yb, z1)


def write_stl(path):
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            f.write(struct.pack("<12f", nx, ny, nz,
                                a[0], a[1], a[2],
                                b[0], b[1], b[2],
                                c[0], c[1], c[2]))
            f.write(struct.pack("<H", 0))
    print("wrote", path, len(tris), "triangles")


# ---------------------------------------------------------------- body ---
W, H, T, D = 96.0, 70.0, 2.5, 34.5   # outer W/H, wall, body depth

# Front panel (z 0..T) with PIR dome window and camera slot.
slab_boxes(0, W, 0, H, 0, T, [
    (11, 37, 25, 51),   # PIR dome window 26x26, centre (24,38)
    (60, 76, 25, 51),   # camera slot 16x26, centre (68,38)
])

# Side / top walls.
box(0, 0, 0, T, H, D)          # left
box(W - T, 0, 0, W, H, D)      # right
box(T, H - T, 0, W - T, H, D)  # top
# Bottom wall with USB cable slot (x 42..54, open at the build-plate edge).
box(T, 0, 0, 42, T, D)
box(54, 0, 0, W - T, T, D)
box(42, 0, 8, 54, T, D)

# Corner screw bosses (M3 self-tap into 2.8mm pilot).
for cx, cy in [(6, 6), (90, 6), (6, 64), (90, 64)]:
    screw_boss(cx, cy, 3.5, 1.4, T, 34.0)

write_stl(os.path.join(BASE, "doorbell-cam-body.stl"))

# ---------------------------------------------------------------- lid ----
tris.clear()
# Layer A (z D..D+1.5): M3 clearance 3.4mm sq. + wall-mount 5mm sq. holes.
slab_boxes(0, W, 0, H, D, D + 1.5, [
    (4.3, 7.7, 4.3, 7.7), (88.3, 91.7, 4.3, 7.7),
    (4.3, 7.7, 62.3, 65.7), (88.3, 91.7, 62.3, 65.7),
    (45.5, 50.5, 9.5, 14.5), (45.5, 50.5, 55.5, 60.5),
])
# Layer B (z D+1.5..D+3.5): 7mm sq. counterbores so M3 heads sit flush.
slab_boxes(0, W, 0, H, D + 1.5, D + 3.5, [
    (2.5, 9.5, 2.5, 9.5), (86.5, 93.5, 2.5, 9.5),
    (2.5, 9.5, 60.5, 67.5), (86.5, 93.5, 60.5, 67.5),
    (45.5, 50.5, 9.5, 14.5), (45.5, 50.5, 55.5, 60.5),
])

write_stl(os.path.join(BASE, "doorbell-cam-lid.stl"))
