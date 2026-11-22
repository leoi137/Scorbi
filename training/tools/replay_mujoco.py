#!/usr/bin/env python3
"""Replay recorded motor targets in MuJoCo on a flat floor (block B: do the simulators match?).

    python training/tools/replay_mujoco.py scripted.json --dt 0.002 --out replay_mujoco_0.002.json

The input is a recording of the website's scripted gait (50 Hz targets for the 15 motors). The
robot starts in the recording's first pose and the same targets are sent, open loop.
"""
import argparse
import json
import pathlib

import mujoco
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("recording")
parser.add_argument("--dt", type=float, default=0.002)
parser.add_argument("--out", required=True)
args = parser.parse_args()

src = json.loads(pathlib.Path(args.recording).read_text())
joints = src["meta"]["joints"]
m = mujoco.MjModel.from_xml_path(str(ROOT / "scorpion" / "scene.xml"))
m.opt.timestep = args.dt
substeps = round(0.02 / args.dt)
assert [m.joint(j).name for j in range(1, m.njnt)] == joints, "joint order"
assert [m.actuator(a).name for a in range(m.nu)] == joints, "actuator order"

cells = []
for cell in src["cells"]:
    d = mujoco.MjData(m)
    ctrl, q0 = np.array(cell["ctrl"]), np.array(cell["q"][0])
    d.qpos[:3] = [0.0, 0.0, cell["pos"][0][2] - cell["floor_under_start_m"]]
    d.qpos[3:7] = cell["quat"][0]
    d.qpos[7:] = q0
    d.ctrl[:] = ctrl[0]
    mujoco.mj_forward(m, d)
    rec = {"q": [d.qpos[7:].tolist()], "torque": [], "pos": [d.qpos[:3].tolist()], "quat": [d.qpos[3:7].tolist()]}
    for t in range(len(ctrl)):
        d.ctrl[:] = ctrl[t]
        for _ in range(substeps):
            mujoco.mj_step(m, d)
        rec["q"].append(d.qpos[7:].tolist())
        rec["torque"].append(d.actuator_force.tolist())
        rec["pos"].append(d.qpos[:3].tolist())
        rec["quat"].append(d.qpos[3:7].tolist())
    cells.append({"cell": cell["cell"], **rec})
pathlib.Path(args.out).write_text(json.dumps({
    "meta": {"what": f"MuJoCo {mujoco.__version__}, flat floor, {args.dt} s steps", "joints": joints, "rate_hz": 50, "quat_order": "wxyz",
             "solver": {"integrator": int(m.opt.integrator), "cone": int(m.opt.cone), "iterations": int(m.opt.iterations), "impratio": float(m.opt.impratio)}},
    "cells": cells,
}))
print(f"{args.out}: {len(cells)} cells, dt {args.dt}, {substeps} physics steps per control step")
