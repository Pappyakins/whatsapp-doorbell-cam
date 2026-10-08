#!/usr/bin/env python3
"""Realistic assembly renders for the doorbell cam (Blender 4.2, headless).

Renders two views with Cycles CPU:
  render-fitted.png   - transparent body, all components in place, lid raised
  render-exploded.png - parts separated along Z with labels

Run: blender --background --python render_assembly.py
"""
import bpy
import math
import os
import sys

argv = sys.argv
VIEW = "both"
if "--view" in argv:
    VIEW = argv[argv.index("--view") + 1]

CASE = "/home/hatch/workspace/doorbell-cam/case"
OUT_FIT = os.path.join(CASE, "render-fitted.png")
OUT_EXP = os.path.join(CASE, "render-exploded.png")

# ------------------------------------------------------------- clear ---
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# --------------------------------------------------------- materials ---
def make_mat(name, rgb, metallic=0.0, roughness=0.5, alpha=1.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    return m

PETG       = make_mat("PETG", (0.16, 0.18, 0.23), roughness=0.55)
PETG_GHOST = make_mat("PETG_GHOST", (0.16, 0.18, 0.23), roughness=0.4, alpha=0.20)
GREEN = make_mat("PCB_G", (0.04, 0.32, 0.10), roughness=0.6)
BLUE  = make_mat("PCB_B", (0.07, 0.18, 0.52), roughness=0.6)
RED   = make_mat("PCB_R", (0.48, 0.05, 0.05), roughness=0.6)
WHITE = make_mat("WHITE", (0.93, 0.93, 0.90), roughness=0.35)
BLACK = make_mat("BLACK", (0.04, 0.04, 0.04), roughness=0.55)
SHIELD = make_mat("SHIELD", (0.72, 0.73, 0.76), metallic=1.0, roughness=0.35)
BRASS = make_mat("BRASS", (0.70, 0.50, 0.18), metallic=1.0, roughness=0.32)
STEEL = make_mat("STEEL", (0.28, 0.28, 0.30), metallic=1.0, roughness=0.42)
CELL  = make_mat("CELL", (0.08, 0.30, 0.12), metallic=0.25, roughness=0.45)
GLASS = make_mat("GLASS", (0.02, 0.05, 0.14), metallic=0.2, roughness=0.08)
NYLON = make_mat("NYLON", (0.03, 0.03, 0.03), roughness=0.6)
LABELM = make_mat("LABELM", (0.10, 0.16, 0.29), roughness=0.8)

# ----------------------------------------------------------- helpers ---
G = {}
BASE_Z = {}

def grp(n):
    G[n] = []
    return G[n]

def reg(obj, group):
    group.append(obj)
    BASE_Z[obj] = obj.location.z
    return obj

def box(name, dims, loc, mat, group):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.dimensions = dims
    o.data.materials.append(mat)
    return reg(o, group)

def cyl(name, r, h, loc, mat, group, verts=48, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h,
                                        location=loc,
                                        rotation=rotation or (0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return reg(o, group)

def ball(name, r, loc, mat, group, scale_z=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc,
                                         segments=48, ring_count=24)
    o = bpy.context.active_object
    o.name = name
    o.scale[2] = scale_z
    o.data.materials.append(mat)
    return reg(o, group)

def torus(name, R, r, loc, mat, group, rotation=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     location=loc,
                                     rotation=rotation or (0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return reg(o, group)

def import_stl(path, name, mat):
    try:
        bpy.ops.wm.stl_import(filepath=path)
    except Exception:
        bpy.ops.import_mesh.stl(filepath=path)
    o = bpy.context.active_object
    o.name = name
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat)
    return o

# ------------------------------------------------------ case shells ---
body = import_stl(os.path.join(CASE, "doorbell-cam-body.stl"), "Body", PETG)
lid = import_stl(os.path.join(CASE, "doorbell-cam-lid.stl"), "Lid", PETG)
BASE_Z[body] = 0.0
BASE_Z[lid] = 0.0
G["lid"] = [lid]

# -------------------------------------------------------- components ---
g = grp("esp")  # ESP32-CAM at (68,41), long side horizontal
box("esp_pcb", (40.5, 27, 1.6), (68, 41, 6.8), GREEN, g)
box("esp_shield", (18, 20, 3), (58, 41, 9.1), SHIELD, g)
box("esp_cam", (12, 12, 4), (68, 41, 9.6), BLACK, g)
cyl("esp_lens", 4, 2.5, (68, 41, 12.8), GLASS, g)
box("esp_flash", (3, 2, 1), (76, 41, 9.0), WHITE, g)
box("esp_c1", (4, 3, 1.5), (82, 32, 8.6), BLACK, g)
box("esp_c2", (3, 3, 1.5), (52, 50, 8.6), BLACK, g)

g = grp("pir")  # HC-SR501 at (24,41)
box("pir_pcb", (32, 24, 1.6), (24, 41, 5.8), BLUE, g)
ball("pir_dome", 11.5, (24, 41, 14.0), WHITE, g, scale_z=0.75)
box("pir_c1", (5, 4, 2), (14, 34, 7.6), BLACK, g)
box("pir_c2", (5, 4, 2), (34, 48, 7.6), BLACK, g)

g = grp("cell")  # 18650, axis along X at y=14, z=12
cyl("cell", 9, 68, (48, 14, 12), CELL, g, rotation=(0, math.pi / 2, 0))
cyl("cell_pos", 4, 1.2, (82.4, 14, 12), SHIELD, g,
    rotation=(0, math.pi / 2, 0))

g = grp("tie")  # zip tie loop in YZ plane
torus("tie", 10.8, 1.2, (48, 14, 12), NYLON, g, rotation=(0, math.pi / 2, 0))
box("tie_buckle", (5, 4, 3), (48, 14, 23.5), NYLON, g)

g = grp("tp4056")  # charger board beside cradle
box("tp_pcb", (25, 15, 3), (30, 59, 5.0), BLUE, g)
box("tp_usb", (7, 5, 2.5), (30, 59, 7.7), SHIELD, g)
box("tp_c1", (4, 3, 1.5), (22, 55, 7.2), BLACK, g)

g = grp("boost")  # 5V boost beside cradle
box("bst_pcb", (22, 14, 3), (72, 60, 5.0), RED, g)
box("bst_ind", (6, 6, 4), (72, 60, 8.5), BLACK, g)

g = grp("cap")  # 470uF cap
cyl("cap_body", 4, 10, (52, 60, 9.0), BLACK, g)
cyl("cap_top", 4, 0.6, (52, 60, 14.2), SHIELD, g)

g = grp("inserts")  # 4x M3 brass inserts, flush with boss tops
for bx, by in [(8, 8), (88, 8), (8, 62), (88, 62)]:
    cyl(f"ins_{bx}_{by}", 2.3, 5.7, (bx, by, 31.15), BRASS, g)

g = grp("screws")  # 4x M3x10 socket-head (assembled above lid at z=0)
for bx, by in [(8, 8), (88, 8), (8, 62), (88, 62)]:
    cyl(f"scr_shaft_{bx}_{by}", 1.5, 10, (bx, by, 13.0), STEEL, g)
    cyl(f"scr_head_{bx}_{by}", 2.75, 3, (bx, by, 19.5), STEEL, g)

g = grp("wallscrews")  # 2x wall screws (exploded view only)
for mx, my in [(48, 12), (48, 58)]:
    cyl(f"ws_shaft_{mx}_{my}", 2.2, 22, (mx, my, 16.0), STEEL, g)
    cyl(f"ws_head_{mx}_{my}", 4.5, 2.5, (mx, my, 28.2), STEEL, g)
for o in g:
    o.hide_render = True

# ------------------------------------------------ camera/lights/world
bpy.ops.object.camera_add(location=(215, -145, 135))
cam = bpy.context.active_object
cam.data.lens = 55
cam.data.clip_start = 1
cam.data.clip_end = 10000
bpy.context.scene.camera = cam
bpy.ops.object.empty_add(location=(48, 35, 30))
tgt = bpy.context.active_object
tgt.name = "CamTarget"
cc = cam.constraints.new("TRACK_TO")
cc.target = tgt
cc.track_axis = "TRACK_NEGATIVE_Z"
cc.up_axis = "UP_Y"

def area(name, loc, power, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.energy = power
    o.data.size = size
    return o

area("Key", (250, -200, 320), 30000, 150)
area("Fill", (-220, -160, 180), 12000, 120)
area("Rim", (-80, 260, 260), 15000, 120)

w = bpy.context.scene.world
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (1, 1, 1, 1)
bg.inputs["Strength"].default_value = 1.0

s = bpy.context.scene
s.render.engine = "CYCLES"
s.cycles.device = "CPU"
s.cycles.samples = 128
s.cycles.use_denoising = True
try:
    s.cycles.denoiser = "OPENIMAGEDENOISE"
except TypeError:
    pass
s.render.resolution_x = 1600
s.render.resolution_y = 1200
s.render.resolution_percentage = 100
s.render.film_transparent = False
s.render.image_settings.file_format = "PNG"

def set_z(group_names, offset=None, absolute=None):
    for n in group_names:
        for o in G[n]:
            o.location.z = absolute if absolute is not None \
                else BASE_Z[o] + offset

def render(path):
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)

# ------------------------------------------------------- fitted view ---
if VIEW in ("both", "fitted"):
    body.data.materials.clear()
    body.data.materials.append(PETG_GHOST)
    set_z(["lid"], offset=45)
    set_z(["screws"], offset=45)
    tgt.location = (48, 35, 30)
    cam.location = (215, -145, 135)
    render(OUT_FIT)

# ----------------------------------------------------- exploded view ---
if VIEW in ("both", "exploded"):
    body.data.materials.clear()
    body.data.materials.append(PETG)
    OFF = {"inserts": 55, "pir": 95, "esp": 125, "tp4056": 125,
           "boost": 125, "cap": 125, "cell": 160, "tie": 160,
           "lid": 190, "screws": 190, "wallscrews": 205}
    for n, off in OFF.items():
        set_z([n], offset=off)
    for o in G["wallscrews"]:
        o.hide_render = False

    def label(text, loc):
        bpy.ops.object.text_add(location=loc)
        o = bpy.context.active_object
        o.data.body = text
        o.data.size = 9
        c = o.constraints.new("TRACK_TO")
        c.target = cam
        c.track_axis = "TRACK_Z"
        c.up_axis = "UP_Y"
        o.data.materials.append(LABELM)
        return o

    label("brass inserts x4", (-48, 35, 86))
    label("PIR sensor", (-48, 41, 108))
    label("ESP32-CAM", (-48, 41, 138))
    label("TP4056 + boost", (148, 62, 138))
    label("18650 + zip tie", (-48, 14, 172))
    label("lid", (-48, 35, 192))
    label("M3x10", (-48, 35, 206))

    tgt.location = (48, 35, 110)
    cam.location = (380, -300, 270)
    cam.data.lens = 40
    render(OUT_EXP)
    print("done")
