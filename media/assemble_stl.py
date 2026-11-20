#!/usr/bin/env python3
"""Write the whole robot, standing, as one STL: media/scorbi.stl, in millimetres.

    python media/assemble_stl.py

GitHub shows .stl files in a 3D viewer you can turn and zoom, so the README links here.
It is for looking at, not printing: print the separate parts.
"""
import json
import pathlib

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
m = mujoco.MjModel.from_xml_path(str(HERE / "scorpion" / "scene.xml"))
d = mujoco.MjData(m)
stand = json.loads((HERE / "scorpion" / "model.json").read_text())["stand"]
d.qpos[0:3] = (0, 0, stand["base_height"])
d.qpos[3:7] = (1, 0, 0, 0)
for j, q in stand["joints"].items():
    d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)]] = q
mujoco.mj_kinematics(m, d)

tris = []
for g in range(m.ngeom):
    if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] != 2:
        continue
    i = m.geom_dataid[g]
    v = m.mesh_vert[m.mesh_vertadr[i]:m.mesh_vertadr[i] + m.mesh_vertnum[i]]
    f = m.mesh_face[m.mesh_faceadr[i]:m.mesh_faceadr[i] + m.mesh_facenum[i]]
    world = v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
    tris.append(world[f] * 1000.0)
tris = np.concatenate(tris).astype(np.float32)
n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)

rec = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
rec["n"], rec["v"] = n, tris
out = HERE / "media" / "scorbi.stl"
with open(out, "wb") as fh:
    fh.write(b"Scorbi scorpion spider v0.4, standing, millimetres".ljust(80, b" "))
    fh.write(np.uint32(len(tris)).tobytes())
    fh.write(rec.tobytes())
print(f"wrote {out.relative_to(HERE)}: {len(tris)} triangles, {out.stat().st_size / 1e6:.1f} MB")
