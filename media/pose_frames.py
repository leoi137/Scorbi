#!/usr/bin/env python3
"""Pose the robot for the README turntable and write every frame's part positions.

    python media/pose_frames.py <out.npz> [frames]

The robot stands in its standing pose (scorpion/model.json), turns once about its
base and waves its arm and claw twice. Joints are set directly; nothing is simulated.
The .npz holds each mesh's vertices and faces, and each visual part's mesh, material,
position and rotation per frame. media/render.py turns it into images in Blender.
"""
import json
import math
import pathlib
import sys

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
out = pathlib.Path(sys.argv[1])
frames = int(sys.argv[2]) if len(sys.argv) > 2 else 96

m = mujoco.MjModel.from_xml_path(str(HERE / "scorpion" / "scene.xml"))
d = mujoco.MjData(m)
info = json.loads((HERE / "scorpion" / "model.json").read_text())
stand = info["stand"]


def qadr(name):
    return m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, name)]


geoms = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g] == 2]
meshes = sorted({int(m.geom_dataid[g]) for g in geoms})
name = lambda kind, i: mujoco.mj_id2name(m, kind, i)

pos = np.zeros((frames, len(geoms), 3))
quat = np.zeros((frames, len(geoms), 4))
for f in range(frames):
    t = f / frames
    yaw = 2 * math.pi * t
    w = math.sin(4 * math.pi * t)
    d.qpos[:] = 0
    d.qpos[0:3] = (0, 0, stand["base_height"])
    d.qpos[3:7] = (math.cos(yaw / 2), 0, 0, math.sin(yaw / 2))
    for j, q in stand["joints"].items():
        d.qpos[qadr(j)] = q
    d.qpos[qadr("arm_shoulder")] += 0.14 * w
    d.qpos[qadr("arm_elbow")] += 0.20 * math.sin(4 * math.pi * t + 0.9)
    d.qpos[qadr("claw")] += 0.85 * (0.5 - 0.5 * math.cos(4 * math.pi * t))
    mujoco.mj_kinematics(m, d)
    for k, g in enumerate(geoms):
        pos[f, k] = d.geom_xpos[g]
        mujoco.mju_mat2Quat(quat[f, k], d.geom_xmat[g])

arrays = dict(
    pos=pos, quat=quat,
    geom_mesh=np.array([meshes.index(int(m.geom_dataid[g])) for g in geoms]),
    geom_material=np.array([name(mujoco.mjtObj.mjOBJ_MATERIAL, m.geom_matid[g]) for g in geoms]),
    mesh_names=np.array([name(mujoco.mjtObj.mjOBJ_MESH, i) for i in meshes]),
)
for k, i in enumerate(meshes):
    va, vn = m.mesh_vertadr[i], m.mesh_vertnum[i]
    fa, fn = m.mesh_faceadr[i], m.mesh_facenum[i]
    arrays[f"verts{k}"] = m.mesh_vert[va:va + vn].copy()
    arrays[f"faces{k}"] = m.mesh_face[fa:fa + fn].copy()
for mat in ("cream", "coral", "mint", "eye", "motor"):
    arrays[f"rgba_{mat}"] = m.mat_rgba[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_MATERIAL, mat)].copy()
np.savez_compressed(out, **arrays)
lo = pos[0].min(0); hi = pos[0].max(0)
print(f"{frames} frames, {len(geoms)} parts, {len(meshes)} meshes; part centres span {lo.round(3)} to {hi.round(3)}; equality constraints: {m.neq}")
