#!/usr/bin/env python3
"""Compare recorded runs at their final checkpoint: one row per run.

    python training/tools/summarize.py <run folder> [<run folder> ...] [--json out.json]

Reads each run's eval/ folder (written by evaluate.py). Needs numpy. Columns:
  pass        episodes that passed their test, of 416 (13 commands x 32 seeds)
  90% at      the first saved iteration where 375 or more passed
  fwd, turn   speed achieved on forward 0.12 m/s and turn-left 1.0 rad/s
  slow park   share of time parked on forward 0.06 m/s (the command most likely to be given up on)
  flip        share of control steps on which an action changes sign
  red         share of episodes red on the motor mark; at-limit = median share of time a motor is at its limit
  steps/s     lift-offs per foot per second on the forward commands
  lift mm     how high a swinging foot is above its resting height, 90th percentile, forward 0.12 m/s (100 Hz recordings)
  tilt        largest tilt on the walking commands, degrees
  stand drift median drift over 20 s when told to stand, mm
"""
import json
import pathlib
import statistics as st
import sys

import numpy as np

FOOT_AT_REST = 0.0125
args = [a for a in sys.argv[1:] if not a.startswith("--")]
out_path = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
if out_path in args:
    args.remove(out_path)
rows = []
for folder in args:
    run = pathlib.Path(folder)
    ev = run / "scorbi" / "eval"
    index = [json.loads(line) for line in (ev / "index_seeds.jsonl").read_text().splitlines()]
    last = index[-1]["iteration"]
    e = json.loads((ev / str(last) / "episodes.json").read_text())
    eps, cells = e["episodes"], {c["cell"]: c for c in e["summary"]}
    manifest = json.loads((run / "scorbi" / "manifest.json").read_text())
    lift = None
    if (ev / str(last) / "detail.npz").exists():
        d = np.load(ev / str(last) / "detail.npz")
        cols = json.loads(str(d["columns"]))
        heights = []
        for k in range(len(d["episode"])):
            i = int(d["episode"][k])
            if eps[i]["cell"] != "forward_top" or d["rows"][k] != 2001:
                continue
            x = d["data"][d["start"][k] + 200 : d["start"][k] + 2001]
            pos = x[:, slice(*cols["foot_pos"])].reshape(-1, 4, 3)
            force = np.linalg.norm(x[:, slice(*cols["foot_force"])].reshape(-1, 4, 3), axis=2)
            heights.append(pos[:, :, 2][force < 0.3])
        heights = np.concatenate(heights) if heights else np.zeros(0)
        lift = float(np.percentile(heights, 90) - FOOT_AT_REST) * 1000 if heights.size else 0.0
    walking = [x for x in eps if any(x["command"].values())]
    measured = cells["forward_top"].get("measured_terms") or {}
    rows.append({
        "run": run.name, "task": manifest.get("task"), "seed": manifest.get("seed"), "what": manifest.get("meta", {}).get("what"), "iteration": last,
        "passed": last and sum(x["success"] for x in eps), "episodes": len(eps), "falls": sum(x["fell"] for x in eps),
        "first_iteration_90_percent": next((r["iteration"] for r in index if r["passed"] >= 0.9 * r["episodes"]), None),
        "cells_passed": {c: cells[c]["passed"] for c in cells},
        "forward_top_m_s": cells["forward_top"]["forward_m_s"], "turn_left_rad_s": cells["turn_left"]["turn_rad_s"],
        "forward_slow_parked": cells["forward_slow"]["parked_share"],
        "flip_rate": st.mean(x["action_flip_rate"] for x in eps), "red_share": sum(x["motor_mark"] == "red" for x in eps) / len(eps),
        "green_share": sum(x["motor_mark"] == "green" for x in eps) / len(eps),
        "at_limit_median": st.median(x["share_of_time_at_limit_max"] for x in eps),
        "torque_mean_max_median_n_m": st.median(max(x["torque_mean_n_m"][:12]) for x in eps),
        "gait": e["gait"], "lift_offs_per_foot_per_second": (e["gait_stats"] or {}).get("lift_offs_per_foot_per_second"),
        "swing_lift_p90_mm": lift, "largest_tilt_walking_deg": max(x["largest_tilt_deg"] for x in walking),
        "stand_drift_median_mm": st.median(x["drift_m"] for x in eps if x["cell"] == "stand") * 1000,
        "fail_labels": index[-1]["fail_labels"], "measured_forward_top": measured,
        "labels_seen_at_any_checkpoint": sorted({k for r in index for k in r["fail_labels"]}),
        "training_falls": json.loads((run / "scorbi" / "finished.json").read_text()).get("falls"),
    })
f = lambda v, w, p=2: (" " * (w - 1) + "-") if v is None else f"{v:>{w}.{p}f}"  # noqa: E731
print(f"{'run':24} {'pass':>4} {'90% at':>6} {'fwd':>6} {'turn':>5} {'slow park':>9} {'flip':>5} {'red':>4} {'at-limit':>8} {'steps/s':>7} {'lift mm':>7} {'tilt':>5} {'stand drift':>11}  gait, labels at the end")
for r in rows:
    name = r["run"].split("_", 2)[-1]
    print(f"{name:24} {r['passed']:>4} {str(r['first_iteration_90_percent'] if r['first_iteration_90_percent'] is not None else '-'):>6} {f(r['forward_top_m_s'], 6, 3)} {f(r['turn_left_rad_s'], 5)} {f(r['forward_slow_parked'], 9)}"
          f" {f(r['flip_rate'], 5)} {f(r['red_share'], 4)} {f(r['at_limit_median'], 8)} {f(r['lift_offs_per_foot_per_second'], 7, 1)} {f(r['swing_lift_p90_mm'], 7, 1)} {f(r['largest_tilt_walking_deg'], 5, 1)}"
          f" {f(r['stand_drift_median_mm'], 11, 0)}  {r['gait']}, {r['fail_labels']}")
if out_path:
    pathlib.Path(out_path).write_text(json.dumps(rows, indent=1))
