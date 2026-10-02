#!/usr/bin/env python3
"""Generate STL files for the WhatsApp Doorbell Cam enclosure — pebble style.

Design (all mm):
  - Rounded-rectangle "pebble" body, 96 x 70 x 34.5, 2.5 wall, smooth
    extruded silhouette (no faceted edges).
  - Front face with two raised circular bezels (smooth bores):
      * PIR bezel: 26 mm bore for the HC-SR501 Fresnel dome (23 mm)
      * Camera bezel: 20 mm bore covering the ESP32-CAM lens + flash LED
  - USB cable notch in the bottom wall.
  - 4x corner bosses take M3 self-tapping screws (2.8 mm pilot).
  - Lid: matching rounded back plate, 3 mm, with M3 clearance holes and
    2x 5 mm wall-mount holes (single piece — no split layers).

Print: body FRONT-FACE-DOWN, lid flat. No supports. PETG recommended.
Only the Python standard library is used.

Outputs: doorbell-cam-body.stl, doorbell-cam-lid.stl (binary STL, mm).
"""
import struct
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))

tris = []


def tri(a, b, c):
    tris.append((tuple(a), tuple(b), tuple(c)))


def box(x0, y0, z0, x1, y1, z1):
    tri((x0, y0, z0), (x1, y1, z0), (x1, y0, z0))
    tri((x0, y0, z0), (x0, y1, z0), (x1, y1, z0))
    tri((x0, y0, z1), (x1, y0, z1), (x1, y1, z1))
    tri((x0, y0, z1), (x1, y1, z1), (x0, y1, z1))
    tri((x0, y1, z0), (x1, y1, z1), (x1, y1, z0))
    tri((x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
    tri((x0, y0, z0), (x1, y0, z0), (x1, y0, z1))
    tri((x0, y0, z0), (x1, y0, z1), (x0, y0, z1))
    tri((x1, y0, z0), (x1, y1, z0), (x1, y1, z1))
    tri((x1, y0, z0), (x1, y1, z1), (x1, y0, z1))
    tri((x0, y0, z0), (x0, y1, z1), (x0, y1, z0))
    tri((x0, y0, z0), (x0, y0, z1), (x0, y1, z1))


# ------------------------------------------------------------- 2D loops ---
def _loop_elements(cx, cy, w, h, r):
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - h / 2, cy + h / 2
    return [
        ('line', (x1, y0 + r), (x1, y1 - r)),
        ('arc', (x1 - r, y1 - r), 0.0, math.pi / 2, r),
        ('line', (x1 - r, y1), (x0 + r, y1)),
        ('arc', (x0 + r, y1 - r), math.pi / 2, math.pi, r),
        ('line', (x0, y1 - r), (x0, y0 + r)),
        ('arc', (x0 + r, y0 + r), math.pi, 3 * math.pi / 2, r),
        ('line', (x0 + r, y0), (x1 - r, y0)),
        ('arc', (x1 - r, y0 + r), 3 * math.pi / 2, 2 * math.pi, r),
    ]


def _element_point(el, t):
    kind = el[0]
    if kind == 'line':
        (ax, ay), (bx, by) = el[1], el[2]
        return (ax + (bx - ax) * t, ay + (by - ay) * t)
    (_, (ccx, ccy), a0, a1, rr) = el
    a = a0 + (a1 - a0) * t
    return (ccx + rr * math.cos(a), ccy + rr * math.sin(a))


def _element_len(el):
    if el[0] == 'line':
        (ax, ay), (bx, by) = el[1], el[2]
        return math.hypot(bx - ax, by - ay)
    return (el[3] - el[2]) * el[4]


def rounded_rect_loop(cx, cy, w, h, r, z, n=96, skip_elements=()):
    """CCW rounded-rectangle loop, evenly sampled. skip_elements: indices of
    elements to leave out (returns open polyline pieces)."""
    els = _loop_elements(cx, cy, w, h, r)
    lens = [_element_len(e) for e in els]
    pieces, cur = [], []
    for ei, el in enumerate(els):
        if ei in skip_elements:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        # sample this element with count proportional to its length
        total = sum(lens[e] for e in range(len(els)) if e not in skip_elements)
        m = max(2, int(round(n * lens[ei] / sum(lens))))
        for k in range(m):
            x, y = _element_point(el, k / m)
            cur.append((x, y, z))
    if cur:
        pieces.append(cur)
    return pieces


def strip_open(p0, p1, flip=False):
    """Connect two same-length open polylines with quads (no wraparound)."""
    n = min(len(p0), len(p1))
    for i in range(n - 1):
        j = i + 1
        if not flip:
            tri(p0[i], p0[j], p1[j])
            tri(p0[i], p1[j], p1[i])
        else:
            tri(p0[i], p1[j], p0[j])
            tri(p0[i], p1[i], p1[j])


def strip_closed(p0, p1, flip=False):
    n = min(len(p0), len(p1))
    for i in range(n):
        j = (i + 1) % n
        if not flip:
            tri(p0[i], p0[j], p1[j])
            tri(p0[i], p1[j], p1[i])
        else:
            tri(p0[i], p1[j], p0[j])
            tri(p0[i], p1[i], p1[j])


def _ring(cx, cy, r, z, n):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]


def tube(cx, cy, r_out, r_in, z0, z1, n=48):
    """Hollow vertical cylinder (bezel / boss), open at the bottom."""
    o0, o1 = _ring(cx, cy, r_out, z0, n), _ring(cx, cy, r_out, z1, n)
    i0, i1 = _ring(cx, cy, r_in, z0, n), _ring(cx, cy, r_in, z1, n)
    for k in range(n):
        j = (k + 1) % n
        tri(o0[k], o0[j], o1[j])      # outer wall
        tri(o0[k], o1[j], o1[k])
        tri(i0[k], i1[j], i0[j])      # inner bore (faces the axis)
        tri(i0[k], i1[k], i1[j])
        tri(o1[k], o1[j], i1[j])      # top annulus
        tri(o1[k], i1[j], i1[k])


def screw_boss(cx, cy, z0, z1):
    tube(cx, cy, 3.5, 1.4, z0, z1, n=32)


def in_rounded_rect(x, y, cx, cy, w, h, r):
    dx = abs(x - cx) - (w / 2 - r)
    dy = abs(y - cy) - (h / 2 - r)
    if dx <= 0 and dy <= 0:
        return True
    if dx <= 0:
        return dy <= r
    if dy <= 0:
        return dx <= r
    return dx * dx + dy * dy <= r * r


def voxel_plate(cx, cy, w, h, r, z0, z1, holes, voxel=1.0):
    """Flat plate with circular holes, built from 1 mm voxels.

    holes: list of (hx, hy, hr) — keep-out circles."""
    nx, ny = int(w / voxel), int(h / voxel)
    for ix in range(nx):
        for iy in range(ny):
            x = cx - w / 2 + (ix + 0.5) * voxel
            y = cy - h / 2 + (iy + 0.5) * voxel
            if not in_rounded_rect(x, y, cx, cy, w, h, r):
                continue
            if any((x - hx) ** 2 + (y - hy) ** 2 < hr ** 2
                   for hx, hy, hr in holes):
                continue
            box(x - voxel / 2, y - voxel / 2, z0,
                x + voxel / 2, y + voxel / 2, z1)


def write_stl(path):
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            f.write(struct.pack("<12f",
                                uy * vz - uz * vy, uz * vx - ux * vz,
                                ux * vy - uy * vx,
                                a[0], a[1], a[2], b[0], b[1], b[2],
                                c[0], c[1], c[2]))
            f.write(struct.pack("<H", 0))
    print("wrote", path, len(tris), "triangles")


# ================================================================= body ==
CX, CY = 48.0, 35.0
W, H, R = 96.0, 70.0, 12.0          # outer silhouette
WI, HI, RI = 91.0, 65.0, 9.5        # inner (2.5 wall)
T, D = 2.5, 34.5                     # front plate thickness, body depth
PIR = (24.0, 38.0)                   # PIR bezel centre
CAM = (68.0, 38.0)                   # camera bezel centre

# -- shell walls, full height, except the bottom straight (boxes handle it)
# element 6 is the bottom straight; build the rest as open strips.
for z0, z1 in [(0, D)]:
    po = rounded_rect_loop(CX, CY, W, H, R, z0, skip_elements=(6,))
    po1 = rounded_rect_loop(CX, CY, W, H, R, z1, skip_elements=(6,))
    pi = rounded_rect_loop(CX, CY, WI, HI, RI, z0, skip_elements=(6,))
    pi1 = rounded_rect_loop(CX, CY, WI, HI, RI, z1, skip_elements=(6,))
    for a0, a1, b0, b1 in zip(po, po1, pi, pi1):
        strip_open(a0, a1)              # outer wall
    for a0, a1, b0, b1 in zip(pi, pi1, po, po1):
        strip_open(a0, a1, flip=True)   # inner wall
    for a0, a1, b0, b1 in zip(po, po1, pi, pi1):
        # top rim annulus at z1
        n = min(len(a1), len(b1))
        for k in range(n - 1):
            j = k + 1
            tri(a1[k], a1[j], b1[j])
            tri(a1[k], b1[j], b1[k])

# -- bottom straight wall as solid boxes, with the USB cable notch
# (notch: x 41..55, z 2.5..8, through the 2.5 wall)
box(12, 0, 0, 41, T, D)
box(55, 0, 0, 84, T, D)
box(41, 0, 0, 55, T, T)      # below the notch
box(41, 0, 8, 55, T, D)      # above the notch

# -- front face: inset voxel plate (stepped edge buried in the walls)
voxel_plate(CX, CY, 93, 67, 10.5, 0, T, [
    (PIR[0], PIR[1], 16.7),   # clearance around PIR bezel tube
    (CAM[0], CAM[1], 13.7),   # clearance around camera bezel tube
])

# -- raised circular bezels (smooth bores, 2.5 proud of the face)
tube(PIR[0], PIR[1], 17.0, 13.0, 0, 5.0)    # PIR: 26 mm bore
tube(CAM[0], CAM[1], 14.0, 10.0, 0, 5.0)    # camera: 20 mm bore

# -- corner screw bosses
for bx, by in [(8, 8), (88, 8), (8, 62), (88, 62)]:
    screw_boss(bx, by, T, 34.0)

write_stl(os.path.join(BASE, "doorbell-cam-body.stl"))

# ================================================================= lid ===
tris.clear()
LZ0, LZ1 = D, D + 3.0
# smooth outer ring
ro0 = rounded_rect_loop(CX, CY, W, H, R, LZ0)
ro1 = rounded_rect_loop(CX, CY, W, H, R, LZ1)
ri0 = rounded_rect_loop(CX, CY, WI, HI, RI, LZ0)
ri1 = rounded_rect_loop(CX, CY, WI, HI, RI, LZ1)
strip_closed(ro0[0], ro1[0])
strip_closed(ri0[0], ri1[0], flip=True)
strip_closed(ro1[0], ri1[0])   # top annulus
# inset voxel plate with round holes (single piece)
voxel_plate(CX, CY, 93, 67, 10.5, LZ0, LZ1, [
    (8, 8, 1.7), (88, 8, 1.7), (8, 62, 1.7), (88, 62, 1.7),  # M3 clearance
    (48, 12, 2.5), (48, 58, 2.5),                            # wall mount
])

write_stl(os.path.join(BASE, "doorbell-cam-lid.stl"))
