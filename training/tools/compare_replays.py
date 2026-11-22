#!/usr/bin/env python3
"""Compare replays of the same motor targets in different simulators (block B).

    python training/tools/compare_replays.py scripted.json name=replay.json [name=replay.json ...] [--out=table.json]

The first file is the recording that holds the targets. For each cell and simulator it prints how
far the body went (in the frame of its starting heading), the leg tracking error, and the torques.
"""
import json
import math
import sys

import numpy as np


def yaw(q):  # wxyz
    w, x, y, z = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def tilt(q):
    w, x, y, z = q
    return math.degrees(math.acos(max(-1.0, min(1.0, 1 - 2 * (x * x + y * y)))))


src = json.load(open(sys.argv[1]))
runs = {"website": src}
out = None
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    if name == "--out":
        out = path
        continue
    runs[name] = json.load(open(path))
targets = {c["cell"]: np.array(c["ctrl"]) for c in src["cells"]}
rows = []
print(f"{'cell':13} {'simulator':16} {'fwd m':>7} {'left m':>7} {'turn rad':>8} {'height mm':>9} {'tilt':>5} {'track deg':>9} {'peak Nm':>7} {'mean Nm':>7} {'legs vs website deg':>19}")
for cell in targets:
    ref = None
    for name, run in runs.items():
        c = next((c for c in run["cells"] if c["cell"] == cell), None)
        if c is None:
            continue
        pos, quat, q, torque = np.array(c["pos"]), np.array(c["quat"]), np.array(c["q"]), np.abs(np.array(c["torque"]))
        y0 = yaw(quat[0])
        d = pos[-1, :2] - pos[0, :2]
        fwd, left = math.cos(y0) * d[0] + math.sin(y0) * d[1], -math.sin(y0) * d[0] + math.cos(y0) * d[1]
        turn = float(np.sum((np.diff([yaw(v) for v in quat]) + math.pi) % (2 * math.pi) - math.pi))
        track = math.degrees(float(np.sqrt(np.mean((targets[cell][:, :12] - q[1:, :12]) ** 2))))
        if ref is None:
            ref = q
        apart = math.degrees(float(np.sqrt(np.mean((q[:, :12] - ref[:, :12]) ** 2))))
        row = {"cell": cell, "simulator": name, "forward_m": fwd, "left_m": left, "turn_rad": turn, "height_mm": float(np.mean(pos[50:, 2]) * 1000),
               "largest_tilt_deg": max(tilt(v) for v in quat), "tracking_rms_deg": track, "torque_peak_n_m": float(torque[:, :12].max()),
               "torque_mean_max_n_m": float(torque[:, :12].mean(0).max()), "legs_rms_from_website_deg": apart}
        rows.append(row)
        print(f"{cell:13} {name:16} {fwd:7.3f} {left:7.3f} {turn:8.2f} {row['height_mm']:9.1f} {row['largest_tilt_deg']:5.1f} {track:9.2f} {row['torque_peak_n_m']:7.2f} {row['torque_mean_max_n_m']:7.2f} {apart:19.2f}")
    print()
if out:
    json.dump(rows, open(out, "w"), indent=1)
