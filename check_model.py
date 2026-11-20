#!/usr/bin/env python3
"""Check the generated model against the CAD, then check that it stands.

    python check_model.py

Fails (exit 1) when a foot or the claw is more than 1 mm from where the CAD puts it, when the mass is off,
or when the robot does not stand on its motors.
"""
import math
import pathlib
import sys

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cad"))
sys.path.insert(0, str(HERE))

import assembly as A  # noqa: E402
import build_model as BM  # noqa: E402

problems = []
m = mujoco.MjModel.from_xml_path(str(HERE / "scorpion" / "scene.xml"))
d = mujoco.MjData(m)

names = [m.joint(i).name for i in range(1, m.njnt)]
if names != [n for n, _, _ in BM.JOINT_ORDER]:
    problems.append(f"joint order {names}")
mass = m.body_subtreemass[m.body("base").id] * 1000
print(f"mass {mass:.0f} g")
if abs(mass - BM.LUMP) > 1:
    problems.append(f"mass {mass:.0f} g")

# the CAD at its standing pose, moved into the model's frame
mujoco.mj_resetDataKeyframe(m, d, 0)
mujoco.mj_forward(m, d)
q = dict(A.REST)
q["grip"] = BM.ARM_STAND["claw"]
F = A.frames(q)


def cad_world(p):
    v = BM.W[:3, :3] @ (np.asarray(p, float) - np.array([0, 0, BM.HIP_Z])) * BM.MM
    return v + np.array([0, 0, BM.BASE_HEIGHT])


for leg, i in BM.CAD_LEG.items():
    err = np.linalg.norm(d.xpos[m.body(f"{leg}_foot").id] - cad_world(F[f"foot{i}"][:3, 3])) * 1000
    print(f"{leg} foot {err:.3f} mm from the CAD")
    if err > 1:
        problems.append(f"{leg} foot is {err:.1f} mm off")
grip = m.site("grip").id
local = d.site_xmat[grip].reshape(3, 3) @ np.array([0, 0, 0.00125])  # the site sits 1.25 mm below the CAD's grip line
err = np.linalg.norm(d.site_xpos[grip] + local - cad_world((F["forearm"] @ np.array([A.LH, 0, 0, 1.0]))[:3])) * 1000
print(f"claw {err:.3f} mm from the CAD")
if err > 1:
    problems.append(f"claw is {err:.1f} mm off")

# stand for 5 s on the motors, then drop from 5 cm
for label, lift in (("stand", 0.0), ("drop from 5 cm", 0.05)):
    mujoco.mj_resetDataKeyframe(m, d, 0)
    d.qpos[2] += lift
    for _ in range(2500):
        mujoco.mj_step(m, d)
    tilt = math.degrees(2 * math.acos(min(1.0, abs(d.qpos[3]))))
    effort = np.abs(d.actuator_force[:12]).max() / BM.MOTOR["effort"] * 100
    print(f"{label}: base at {d.qpos[2] * 1000:.1f} mm, tilt {tilt:.2f} degrees, busiest leg motor at {effort:.0f}% of stall")
    if not (0.06 < d.qpos[2] < 0.08) or tilt > 2:
        problems.append(f"{label}: does not stand")

if problems:
    print("PROBLEMS:", *problems, sep="\n  ")
    sys.exit(1)
print("ok")
