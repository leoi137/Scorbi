"""Render the README turntable in Blender, from the frames media/pose_frames.py wrote.

    blender --factory-startup --background --python media/render.py -- \
        <frames.npz> <out_dir> <width> <height> <samples> [first last]

Writes <out_dir>/frame_0000.png and so on: the robot and its shadow on a
transparent background, to be laid over a backdrop afterwards. Uses Cycles on
the GPU when there is one (EEVEE renders black in --background on macOS).
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
npz_path, out_dir = argv[0], argv[1]
width, height, samples = int(argv[2]), int(argv[3]), int(argv[4])
data = np.load(npz_path)
nframes = data["pos"].shape[0]
first = int(argv[5]) if len(argv) > 5 else 0
last = int(argv[6]) if len(argv) > 6 else nframes - 1

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)


def lin(c):
    """sRGB to linear, for colours given as they should look."""
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


# ------------------------------------------------------------------ materials
def material(name, rgb, roughness, coat=0.0, bevel=0.0007):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*lin(rgb), 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    if bevel:
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.samples = 6
        bev.inputs["Radius"].default_value = bevel
        nt.links.new(bev.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


rgb = lambda k: [float(x) for x in data[f"rgba_{k}"][:3]]
MATS = {
    "cream": material("cream", rgb("cream"), 0.42),
    "coral": material("coral", rgb("coral"), 0.42),
    "mint": material("mint", rgb("mint"), 0.42),
    "eye": material("eye", (0.015, 0.016, 0.02), 0.08, coat=1.0, bevel=0.0),
    "motor": material("motor", (0.13, 0.135, 0.15), 0.5, bevel=0.0004),
}

# ------------------------------------------------------------------ meshes, smooth where the surface is smooth
meshes = []
for k, mname in enumerate(data["mesh_names"]):
    me = bpy.data.meshes.new(str(mname))
    me.from_pydata(data[f"verts{k}"].tolist(), [], data[f"faces{k}"].tolist())
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if not e.is_manifold or e.calc_face_angle(math.pi) > math.radians(32):
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    me.materials.append(None)  # one slot, filled per part below: one mesh can carry different colours
    meshes.append(me)

parts = []
for g, (mi, mat) in enumerate(zip(data["geom_mesh"], data["geom_material"])):
    ob = bpy.data.objects.new(f"part{g}", meshes[int(mi)])
    ob.rotation_mode = "QUATERNION"
    scene.collection.objects.link(ob)
    ob.material_slots[0].link = "OBJECT"
    ob.material_slots[0].material = MATS[str(mat)]
    parts.append((ob, str(mat)))

pos, quat = data["pos"], data["quat"]
for f in range(nframes):
    for g, (ob, _) in enumerate(parts):
        ob.location = pos[f, g].tolist()
        ob.rotation_quaternion = quat[f, g].tolist()
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_quaternion", frame=f)

# ------------------------------------------------------------------ floor that only catches the shadow
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
floor = bpy.context.active_object
floor.is_shadow_catcher = True

# ------------------------------------------------------------------ lights and world
CENTER = Vector((0.015, 0.0, 0.115))


def area(name, at, power, size, color):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.size, li.color = power, size, color
    li.shape = "DISK"
    ob = bpy.data.objects.new(name, li)
    ob.location = CENTER + Vector(at)
    ob.rotation_euler = (CENTER - ob.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)


area("key", (0.55, -0.75, 0.85), 70, 0.7, (1.0, 0.94, 0.86))
area("fill", (0.25, 0.9, 0.35), 25, 1.0, (0.86, 0.91, 1.0))
area("rim", (-0.9, 0.2, 0.75), 140, 0.5, (0.9, 0.95, 1.0))

world = bpy.data.worlds.new("studio")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.045, 0.05, 0.058, 1)
bg.inputs["Strength"].default_value = 1.0
scene.world = world

# ------------------------------------------------------------------ camera
cam = bpy.data.cameras.new("cam")
cam.lens = 70
cam.sensor_width = 36
cam_ob = bpy.data.objects.new("cam", cam)
az, el, dist = math.radians(-38), math.radians(19), 1.2
cam_ob.location = CENTER + dist * Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
cam_ob.rotation_euler = (CENTER - cam_ob.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(cam_ob)
scene.camera = cam_ob

# ------------------------------------------------------------------ render settings
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("METAL", "OPTIX", "CUDA", "HIP"):
    try:
        prefs.compute_device_type = kind
    except TypeError:
        continue
    prefs.get_devices()
    gpus = [d for d in prefs.devices if d.type != "CPU"]
    if gpus:
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
        break
print("cycles device:", scene.cycles.device)
scene.cycles.samples = samples
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Punchy", "Punchy"):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        pass

os.makedirs(out_dir, exist_ok=True)
for f in range(first, last + 1):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(out_dir, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath, flush=True)
