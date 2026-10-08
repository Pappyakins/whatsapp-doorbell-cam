#!/usr/bin/env python3
"""Assembly drawing (PDF) for the WhatsApp Doorbell Cam pebble enclosure.

Page 1: dimensioned views of body + lid. Page 2: exploded assembly,
parts list, wiring and steps. All dimensions in mm, matching
generate_case.py. Run with the project venv.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrow, Polygon, Rectangle

BASE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(BASE, "doorbell-cam-assembly-drawing.pdf")

NAVY = "#1b2a4a"
GOLD = "#c9a227"
GREY = "#666666"
LIGHT = "#e8ecf3"

PIR = (24.0, 41.0)
CAM = (68.0, 41.0)
BOSS = [(8, 8), (88, 8), (8, 62), (88, 62)]
MOUNT = [(48, 12), (48, 58)]


def rrect_pts(x0, y0, w, h, r, seg=10):
    pts = []
    for cx, cy, a0 in ((x0 + w - r, y0 + h - r, 0), (x0 + r, y0 + h - r, 90),
                       (x0 + r, y0 + r, 180), (x0 + w - r, y0 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def outline(ax, x0=0, y0=0, w=96, h=70, r=12, lw=1.6, color=NAVY, ls="-"):
    ax.add_patch(Polygon(rrect_pts(x0, y0, w, h, r), closed=True, fill=False,
                         lw=lw, edgecolor=color, linestyle=ls))


def centre_mark(ax, x, y, s=3.0, color=GREY):
    ax.plot([x - s, x + s], [y, y], color=color, lw=0.7)
    ax.plot([x, x], [y - s, y + s], color=color, lw=0.7)


def dim_h(ax, x1, x2, y, text, dy=2.6, color=GREY):
    ax.annotate("", xy=(x1, y), xytext=(x2, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=0.8))
    ax.text((x1 + x2) / 2, y + dy, text, ha="center", va="bottom",
            fontsize=7.5, color=NAVY)


def dim_v(ax, y1, y2, x, text, dx=2.2, color=GREY):
    ax.annotate("", xy=(x, y1), xytext=(x, y2),
                arrowprops=dict(arrowstyle="<->", color=color, lw=0.8))
    ax.text(x + dx, (y1 + y2) / 2, text, ha="left", va="center",
            fontsize=7.5, color=NAVY, rotation=90)


def leader(ax, xy, xytext, text):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=7.5, color=NAVY,
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))


def title_block(fig, title, subtitle):
    fig.text(0.045, 0.945, title, fontsize=15, weight="bold", color=NAVY)
    fig.text(0.045, 0.918, subtitle, fontsize=8.5, color=GREY)
    fig.text(0.955, 0.945, "Rev 2026-10-08", fontsize=8, color=GREY,
             ha="right")
    fig.text(0.955, 0.918, "Units: mm · JakinsCraft", fontsize=8,
             color=GREY, ha="right")
    fig.add_artist(Rectangle((0.04, 0.905), 0.92, 0.002,
                             transform=fig.transFigure, color=GOLD))


def view_title(ax, x, y, text):
    ax.text(x, y, text, ha="center", fontsize=9, weight="bold", color=NAVY)


# ============================================================ PAGE 1 =====
fig1 = plt.figure(figsize=(11, 8.5))
title_block(fig1, "WhatsApp Doorbell Cam — Pebble Enclosure",
            "Dimensioned views · Body (A) and Lid (B) · STLs in the case folder")

# ---- front view of body
ax = fig1.add_axes([0.05, 0.31, 0.44, 0.57])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-18, 112); ax.set_ylim(-17, 88)
outline(ax)
for (x, y, r_out, r_bore) in ((*PIR, 17, 13), (*CAM, 14, 10)):
    ax.add_patch(Circle((x, y), r_out, fill=False, lw=1.6, edgecolor=NAVY))
    ax.add_patch(Circle((x, y), r_bore, fill=False, lw=1.6, edgecolor=NAVY))
    centre_mark(ax, x, y, 3.5)
for bx, by in BOSS:  # behind the front plate -> dashed
    ax.add_patch(Circle((bx, by), 4.0, fill=False, lw=0.9,
                        edgecolor=GREY, linestyle=(0, (3, 2))))
for rx in (24.0, 56.0):  # 18650 saddle ribs (interior, dashed)
    ax.add_patch(Rectangle((rx, 4.0), 6.0, 20.0, fill=False, lw=0.9,
                           edgecolor=GREY, linestyle=(0, (3, 2))))
for ex in (12.0, 82.0):  # cell end stops
    ax.add_patch(Rectangle((ex, 6.0), 2.0, 16.0, fill=False, lw=0.9,
                           edgecolor=GREY, linestyle=(0, (3, 2))))
for sy in (3.0, 21.0):  # zip-tie slots through the floor
    ax.add_patch(Rectangle((46.0, sy), 4.0, 4.0, fill=False, lw=0.9,
                           edgecolor=GREY, linestyle=(0, (3, 2))))
leader(ax, (59, 14), (74, 20),
       "18650 bay: saddle ribs +\nend stops, zip-tie slots")
view_title(ax, 48, 80, "FRONT VIEW — BODY (A)")
dim_h(ax, 0, 96, -8, "96")
dim_v(ax, 0, 70, 104, "70")
ax.annotate("", xy=(0, 75), xytext=(24, 75),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(12, 76.5, "24", ha="center", fontsize=7.5, color=NAVY)
ax.annotate("", xy=(24, 75), xytext=(68, 75),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(46, 76.5, "44", ha="center", fontsize=7.5, color=NAVY)
dim_v(ax, 0, 41, -8, "41")
leader(ax, (PIR[0] - 12, PIR[1] + 13), (-16, 63),
       "PIR bezel Ø34, bore Ø26\n(HC-SR501 dome Ø23)")
leader(ax, (CAM[0] + 10, CAM[1] + 11), (74, 63),
       "Camera bezel Ø28, bore Ø20\n(lens + flash LED)")
leader(ax, (12, 6), (38, -13),
       "4× bosses Ø8 (dashed),\nØ4.1 insert holes behind plate")

# ---- lid view
ax = fig1.add_axes([0.56, 0.60, 0.39, 0.28])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-16, 112); ax.set_ylim(-16, 86)
outline(ax)
for bx, by in BOSS:
    ax.add_patch(Circle((bx, by), 1.7, fill=False, lw=1.2, edgecolor=NAVY))
    ax.add_patch(Circle((bx, by), 2.8, fill=False, lw=0.9, edgecolor=GREY,
                        linestyle=(0, (3, 2))))  # socket-head counterbore
    centre_mark(ax, bx, by, 2.2)
for mx, my in MOUNT:
    ax.add_patch(Circle((mx, my), 2.5, fill=False, lw=1.2, edgecolor=NAVY))
    centre_mark(ax, mx, my, 2.2)
view_title(ax, 48, 82, "LID (B) — OUTSIDE FACE, 5 THICK")
ax.annotate("", xy=(8, -7), xytext=(88, -7),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(48, -12.5, "80 (screw holes)", ha="center", fontsize=7, color=NAVY)
ax.annotate("", xy=(103, 8), xytext=(103, 62),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(106, 35, "54", fontsize=7.5, color=NAVY, rotation=90, va="center")
ax.annotate("", xy=(-8, 12), xytext=(-8, 58),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(-11, 35, "46", fontsize=7.5, color=NAVY, rotation=90, va="center")
leader(ax, (88, 62), (96, 64), "4× Ø3.4 clearance +\nØ5.6 × 3.2 deep counterbore\n(socket heads sit flush)")
leader(ax, (48, 58), (0, 72), "2× Ø5 wall-mount\nholes")

# ---- side view (depth profile)
ax = fig1.add_axes([0.56, 0.335, 0.39, 0.245])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-10, 88); ax.set_ylim(-17, 56)
ax.text(-8, 51, "SIDE VIEW — DEPTH", fontsize=9, weight="bold", color=NAVY)
ax.add_patch(Rectangle((0, 0), 34.5, 46, facecolor="none",
                       edgecolor=NAVY, lw=1.6))            # body
ax.add_patch(Rectangle((0, 0), 2.5, 46, facecolor=LIGHT,
                       edgecolor=NAVY, lw=1.0))            # front plate
ax.add_patch(Rectangle((2.5, 5), 32, 36, facecolor="none",
                       edgecolor=GREY, lw=0.9,
                       linestyle=(0, (3, 2))))             # cavity
ax.add_patch(Rectangle((40, 0), 5, 46, facecolor=LIGHT,
                       edgecolor=NAVY, lw=1.4))            # lid, offset
ax.text(42.5, 49, "LID (B)", fontsize=7.5, color=NAVY, ha="center")
ax.annotate("", xy=(0, -8), xytext=(34.5, -8),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.8))
ax.text(17.25, -13.5, "body depth 34.5", ha="center", fontsize=7,
        color=NAVY)
ax.text(42.5, -13.5, "lid 5", ha="center", fontsize=7, color=NAVY)
leader(ax, (20, 23), (30, 12), "hollow interior\n(2.5 walls all round)")

# ---- bottom view (USB notch)
ax = fig1.add_axes([0.56, 0.10, 0.39, 0.20])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-10, 108); ax.set_ylim(-13, 30)
view_title(ax, 48, 25, "BOTTOM VIEW — USB NOTCH")
ax.add_patch(Rectangle((0, 0), 96, 12, facecolor="none", edgecolor=NAVY,
                       lw=1.6))
ax.add_patch(Rectangle((2.5, 2.5), 91, 7, facecolor="none",
                       edgecolor=GREY, lw=0.8, linestyle=(0, (3, 2))))
ax.add_patch(Rectangle((41, 0), 14, 4.5, facecolor="white",
                       edgecolor=NAVY, lw=1.4))
ax.plot([41, 41], [4.5, 12], color=NAVY, lw=1.2)
ax.plot([55, 55], [4.5, 12], color=NAVY, lw=1.2)
ax.add_patch(Rectangle((66, 0), 12, 4.5, facecolor="white",
                       edgecolor=NAVY, lw=1.4))
ax.plot([66, 66], [4.5, 12], color=NAVY, lw=1.2)
ax.plot([78, 78], [4.5, 12], color=NAVY, lw=1.2)
ax.text(48, -7.5, "notches 5.5 tall behind front plate: main USB x 41–55 "
        "(14 wide), charger USB x 66–78 (12 wide)",
        ha="center", fontsize=7.5, color=NAVY)

# ---- notes
notes = (
    "PRINTING\n"
    "• PETG recommended (porch sun/heat). 0.2 mm layers, 3 walls, 15% infill.\n"
    "• Body prints FRONT-FACE-DOWN; lid prints flat. No supports needed.\n"
    "• Both STLs are single watertight solids — they open directly\n"
    "  in Bambu Studio (fixed 2026-10-02; the old files were not).\n\n"
    "BEFORE A LONG PRINT\n"
    "• Test-fit your parts: HC-SR501 dome is Ø23 (bore Ø26); ESP32-CAM\n"
    "  boards vary slightly between sellers. Print, check, then commit.\n"
    "• USB power cable routes out through the bottom notch.\n"
    "• Press the 4 M3 brass inserts into the bosses (≈200°C iron)\n"
    "  before wiring anything."
)
fig1.text(0.05, 0.035, notes, fontsize=8, color=NAVY, va="bottom",
          family="monospace")
fig1.text(0.955, 0.035, "Powered by @jakinsCraft", fontsize=8, color=GREY,
          ha="right")

# ============================================================ PAGE 2 =====
fig2 = plt.figure(figsize=(11, 8.5))
title_block(fig2, "Assembly — WhatsApp Doorbell Cam",
            "Exploded stack, parts list, wiring and build order")

ax = fig2.add_axes([0.04, 0.08, 0.50, 0.78])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-14, 150); ax.set_ylim(-18, 96)
ax.text(62, 93, "EXPLODED VIEW (schematic, front → back)", fontsize=9,
        weight="bold", color=NAVY, ha="center")
ax.text(62, 88.5, "lens + flash face the Ø20 bore · PIR dome faces the Ø26 bore",
        fontsize=7.5, color=NAVY, ha="center")


def stack_box(x, y, w, h, label, sub, face="none"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=NAVY,
                           lw=1.4))
    ax.text(x + w / 2, y + h + 3.0, label, ha="center", fontsize=8,
            weight="bold", color=NAVY)
    ax.text(x + w / 2, y - 4.5, sub, ha="center", fontsize=6.8, color=GREY)


stack_box(12, 12, 42, 68, "A · BODY", "shell with bosses")
stack_box(64, 24, 30, 44, "BOARDS", "ESP32-CAM · HC-SR501", face=LIGHT)
stack_box(106, 12, 12, 68, "B · LID", "closes the back")
for yy in (26, 68):
    ax.add_patch(FancyArrow(124, yy, -5, 0, width=0.4, head_width=3,
                            head_length=3, color=GOLD, lw=1.4))
ax.text(128, 47, "4× M3×10\nsocket-head\n+ brass inserts", fontsize=7.5,
        color=NAVY, va="center")
ax.plot([33, 33], [12, 3], color=NAVY, lw=1.6)
ax.plot([33, 42], [3, 3], color=NAVY, lw=1.6)
ax.text(37, -3, "charger USB reaches the bottom notch", fontsize=7,
        color=GREY, ha="center")

# ---- parts list
bom = [
    ["#", "Part", "Qty"],
    ["A", "Enclosure body (3D print, PETG)", "1"],
    ["B", "Enclosure lid (3D print, PETG)", "1"],
    ["1", "ESP32-CAM (AI-Thinker) + OV2640", "1"],
    ["2", "HC-SR501 PIR motion sensor", "1"],
    ["3", "M3 × 10 socket-head screws", "4"],
    ["4", "M3 brass heat-set inserts", "4"],
    ["5", "18650 cell + TP4056 + 5V boost + zip tie", "1 ea."],
    ["6", "470 µF capacitor (across 5V/GND)", "1"],
    ["7", "FTDI USB-to-TTL programmer *", "1"],
]
ax2 = fig2.add_axes([0.575, 0.615, 0.40, 0.26])
ax2.axis("off")
ax2.set_title("PARTS LIST   (* FTDI is for flashing only)",
              fontsize=9, color=NAVY, weight="bold", loc="left")
t = ax2.table(cellText=bom, loc="upper left", cellLoc="left",
              colWidths=[0.09, 0.74, 0.17])
t.auto_set_font_size(False); t.set_fontsize(7.6); t.scale(1, 1.45)
for j in range(3):
    t[0, j].set_facecolor(NAVY)
    t[0, j].set_text_props(color="white", weight="bold")

steps = (
    "ASSEMBLY ORDER\n"
    "1. Print A (face-down) and B (flat). No supports.\n"
    "2. Press 4 brass inserts into the body bosses, flush.\n"
    "3. Flash the ESP32-CAM with the FTDI before it goes in.\n"
    "4. Wire the power chain + PIR per the table below;\n"
    "   470 µF across 5V/GND, close to the ESP32-CAM.\n"
    "5. Seat the PIR dome in the Ø26 bore, ESP32-CAM lens\n"
    "   in the Ø20 bore (board long-side horizontal).\n"
    "   VHB tape or hot glue.\n"
    "6. Lay the 18650 in the cradle; zip tie up through one\n"
    "   floor slot, over the cell, down the other slot.\n"
    "7. Tape the TP4056 + boost beside the cradle; line the\n"
    "   charger USB up with its bottom notch.\n"
    "8. Bench-test: wave at the PIR → WhatsApp photo.\n"
    "9. Fix the lid (B) to the wall through the Ø5 holes —\n"
    "   counterbore recesses face OUT.\n"
    "10. Close the body onto the lid with 4× M3×10;\n"
    "    heads sit flush in the counterbores."
)
fig2.text(0.575, 0.575, steps, fontsize=7.8, color=NAVY, va="top",
          family="monospace")

wiring = [
    ["From", "To", "Note"],
    ["18650 +/−", "TP4056 B+/B−", "check polarity first"],
    ["TP4056 OUT", "boost IN", "—"],
    ["boost +5V", "ESP32-CAM 5V", "470 µF across 5V/GND"],
    ["GND", "common everywhere", "battery −, PIR, ESP"],
    ["PIR VCC", "5V rail", "—"],
    ["PIR OUT", "ESP32-CAM GPIO 13", "wake-up trigger"],
]
ax3 = fig2.add_axes([0.575, 0.02, 0.40, 0.25])
ax3.axis("off")
ax3.set_title("WIRING", fontsize=9, color=NAVY, weight="bold", loc="left")
t = ax3.table(cellText=wiring, loc="upper left", cellLoc="left",
              colWidths=[0.26, 0.36, 0.38])
t.auto_set_font_size(False); t.set_fontsize(7.6); t.scale(1, 1.5)
for j in range(3):
    t[0, j].set_facecolor(NAVY)
    t[0, j].set_text_props(color="white", weight="bold")

fig2.text(0.045, 0.035, "Fit check: AI-Thinker ESP32-CAM ≈ 40.5 × 27 mm · "
          "HC-SR501 board ≈ 32 × 24 mm (typical — verify yours)",
          fontsize=7.5, color=GREY)
fig2.text(0.955, 0.035, "Powered by @jakinsCraft", fontsize=8, color=GREY,
          ha="right")

with PdfPages(PDF) as pdf:
    pdf.savefig(fig1)
    pdf.savefig(fig2)
fig1.savefig("/tmp/drawing-p1.png", dpi=110)
fig2.savefig("/tmp/drawing-p2.png", dpi=110)
plt.close("all")
print("wrote", PDF)
