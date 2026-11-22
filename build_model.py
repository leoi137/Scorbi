#!/usr/bin/env python3
"""Build the simulation model of the scorpion spider from its CAD (cad/, v0.5).

    pip install -r requirements.txt
    python build_model.py

Writes
  scorpion/scorpion.xml   MJCF of the robot alone (MuJoCo, or Isaac Lab's MJCF importer)
  scorpion/scene.xml      the robot on a flat floor, to look at in MuJoCo's viewer
  scorpion/scorpion.urdf  the same robot as URDF (Isaac Lab's URDF importer)
  scorpion/model.json     joint ranges, the standing pose and the motor settings, in one place
  scorpion/meshes/        one STL per part, in metres, in the part's own frame
  ../public/sim/robot/    the MJCF again with lighter meshes, for the website. Only when this
                          repository sits at robot/ inside the website's repository.

Frames: x forward, y left, z up. Metres and radians. The base frame sits on the body's centre line at the
height of the hip turn motors. Joint names, their order, zero poses and positive directions follow
the website's src/sim/spec.ts. In particular the knee is 0 when the leg is straight, which is pi minus the CAD's
"angle between thigh and shin".
"""
import json
import math
import pathlib
import struct
import sys
from xml.sax.saxutils import quoteattr

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "cad"))

import assembly as A  # noqa: E402  (the CAD scripts)
import body as B  # noqa: E402
import vendor as V  # noqa: E402
from export import FOUR_WALLS, WALL4  # noqa: E402
from parts import CLAW_X, CLAW_Y, COXA, FOOT_R, GRIP, HIP_Z, L1, L2, LA, LH  # noqa: E402
from prim import Rz, T  # noqa: E402

OUT = HERE / "scorpion"
WEB = ROOT / "public" / "sim" / "robot"
WEB_SKIP = {"hub_tray", "shelf"}  # shut inside the head shell: the website never shows them. Their mass stays in the model
WEB_OUTSIDE = {"tub": lambda: B.tub(inside=False), "deck": lambda: B.deck(inside=False)}  # the website shows these from outside only
HAS_WEB = WEB.parent.is_dir()  # true only inside the website's repository, where this repository is robot/

MM = 0.001
W = Rz(-math.pi / 2)  # CAD frame (x right, y forward, z up) to model frame (x forward, y left, z up)

# ------------------------------------------------------------------ joints (spec.ts order and conventions)
LEG_NAMES = ["fl", "fr", "rl", "rr"]
CAD_LEG = {"fr": 0, "fl": 1, "rr": 2, "rl": 3}  # parts.LEGS is (right, front) = (1, 1) first
D = math.radians
# free ranges from the CAD sweeps (README "Joint limits"), turned into spec.ts conventions
RANGE = {
    "hip_turn": (D(-60), D(60)),
    "hip_lift": (D(-15), D(95)),
    "knee": (D(180 - 105), D(180 - 25)),  # CAD knee angle 25..105 between thigh and shin
    "arm_shoulder": (D(-5), D(100)),
    "arm_elbow": (D(-110), 0.0),
    "claw": (D(-25), D(53)),  # shut, then 78 degrees of travel
}

# Feetech HD-1910-C001 at 6 V, the low end of the 2S pack: 1.18 N m (12 kg cm) stall, 92 rpm with no load.
# kv is the motor's back-EMF (1.18 / 9.6). kp is the v0.3 estimate scaled by the stall torque (4.0 x 1.18 / 0.52).
# Gains, armature and friction are starting estimates, not measurements. Isaac Lab must use the same numbers.
MOTOR = dict(effort=1.18, velocity=9.6, kp=9.0, kv=0.12, armature=0.002, damping=0.05, frictionloss=0.02)

STAND_UP = A.STAND_UP  # the CAD model stands 10 mm taller than its own origin
E0, K0 = A.E0, A.K0  # standing hip lift, and knee angle between thigh and shin
STAND = {"hip_turn": 0.0, "hip_lift": E0, "knee": math.pi - K0}
ARM_STAND = {"arm_shoulder": 1.25, "arm_elbow": -0.55 - 1.25, "claw": D(-22)}
BASE_HEIGHT = (HIP_Z + STAND_UP) * MM + 0.0005  # base origin above the floor when standing, feet just touching

# ------------------------------------------------------------------ colours (print colours from the README)
MATERIALS = {
    "cream": (0.96, 0.92, 0.86, 1),
    "coral": (0.95, 0.55, 0.45, 1),
    "mint": (0.58, 0.85, 0.75, 1),
    "eye": (0.06, 0.07, 0.08, 1),
    "motor": (0.16, 0.17, 0.19, 1),
}
COLOUR = dict(tub="coral", battery_door="coral", deck="coral", hub_tray="coral", shelf="coral", hip="coral", palm_cap="coral",
              lid="cream", shoulder_mount="cream",
              thigh="cream", shin="cream", upper_arm="cream", forearm="cream", foot="mint", finger="mint",
              eye="eye", motor="motor")

# ------------------------------------------------------------------ mass model (same as the CAD's export.py)
RHO, RHO_TPU = 1.24, 1.21  # g/cm3
SKIN, INFILL, INFILL_TPU = 1.2, 0.15, 0.30
LUMP = 1253.0  # g: the v0.5 build pack's figure for the whole robot with its pack. Screws, wires and cables make up the difference.


def frames_at_zero():
    q = dict(yaw=[0.0] * 4, lift=[0.0] * 4, knee=[math.pi] * 4, a1=0.0, a2=0.0, grip=0.0)
    return q, A.frames(q)


def to_model(F):
    G = W @ F
    G = G.copy()
    G[:3, 3] *= MM
    return G


def inv(G):
    R, t = G[:3, :3], G[:3, 3]
    out = np.eye(4)
    out[:3, :3] = R.T
    out[:3, 3] = -R.T @ t
    return out


def quat(R):
    """wxyz quaternion of a rotation matrix."""
    m = R
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = (0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = ((m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s)
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = ((m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s)
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = ((m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s)
    q = np.array(q)
    return q / np.linalg.norm(q) * (1 if q[0] >= 0 else -1)


def rpy(R):
    """URDF roll, pitch, yaw (R = Rz(yaw) Ry(pitch) Rx(roll))."""
    pitch = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    if abs(R[2, 0]) < 0.999999:
        roll = math.atan2(R[2, 1], R[2, 2])
        yaw = math.atan2(R[1, 0], R[0, 0])
    else:
        roll = math.atan2(-R[1, 2], R[1, 1])
        yaw = 0.0
    return roll, pitch, yaw


def f(*v, nd=6):
    return " ".join(f"{x:.{nd}f}".rstrip("0").rstrip(".") if abs(x) > 10 ** -nd else "0" for x in v)


# ------------------------------------------------------------------ meshes and mass properties
def tris_of(solid, tol):
    return A.tess(solid, tol, 0.3 if tol < 0.3 else 0.5).astype(np.float64).reshape(-1, 3, 3)


def moments(t):
    """Volume, first moment and second moment (integral of x x^T) of a closed triangle mesh."""
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    d = np.einsum("ij,ij->i", a, np.cross(b, c))
    vol = d.sum() / 6
    first = ((a + b + c) * d[:, None]).sum(0) / 24
    s = a + b + c
    outer = lambda u: np.einsum("ni,nj->nij", u, u)  # noqa: E731
    second = ((outer(a) + outer(b) + outer(c) + outer(s)) * d[:, None, None]).sum(0) / 120
    return vol, first, second


def area(t):
    return 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum()


def printed_grams(t_mm, tpu, part=""):
    vol = moments(t_mm)[0]
    skin = min(vol, area(t_mm) * SKIN)
    rho, infill = (RHO_TPU, INFILL_TPU) if tpu else (RHO, INFILL)
    return rho * (skin + infill * (vol - skin)) / 1000 * (WALL4 if part in FOUR_WALLS else 1.0)


def apply(G, t):
    return t @ G[:3, :3].T + G[:3, 3]


def write_stl(path, t):
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-15
    t, n = t[keep], n[keep] / ln[keep][:, None]
    with open(path, "wb") as fh:
        fh.write(b"scorpion spider v0.5".ljust(80, b" "))
        fh.write(struct.pack("<I", len(t)))
        rows = np.concatenate([n, t.reshape(-1, 9)], axis=1).astype("<f4")
        for r in rows:
            fh.write(r.tobytes() + b"\0\0")


class Body:
    def __init__(self, name, G):
        self.name, self.G = name, G
        self.mass, self.first, self.second = 0.0, np.zeros(3), np.zeros((3, 3))
        self.visuals = []  # (mesh name, material, 4x4 placement in this body)

    def add_mass(self, grams, t_body):
        vol, first, second = moments(t_body)
        k = grams * 1e-3 / vol
        self.mass += grams * 1e-3
        self.first += first * k
        self.second += second * k

    def inertial(self):
        m = self.mass
        com = self.first / m
        c = self.second - m * np.outer(com, com)
        inertia = np.trace(c) * np.eye(3) - c
        return m, com, inertia


def build():
    q0, F = frames_at_zero()
    bodies = {"base": Body("base", to_model(T(0, 0, HIP_Z) @ Rz(math.pi / 2)))}
    group_body = {"body": "base", "upper_arm": "upper_arm", "forearm": "forearm", "finger": "finger"}
    for leg in LEG_NAMES:
        i = CAD_LEG[leg]
        for part in ("hip", "thigh", "shin", "foot"):
            bodies[f"{leg}_{part}"] = Body(f"{leg}_{part}", to_model(F[f"{part}{i}"]))
            group_body[f"{part}{i}"] = f"{leg}_{part}"
    for part in ("upper_arm", "forearm", "finger"):
        bodies[part] = Body(part, to_model(F[part]))

    fine, light, grams = {}, {}, {}
    print("tessellating parts")
    for name, part, kind, group, M in A.instances(q0):
        if part not in fine:
            solid = A.part(part)
            # coarse first: OpenCascade keeps a shape's finest mesh and would hand it back for the coarse one too
            light[part] = tris_of(WEB_OUTSIDE[part]() if part in WEB_OUTSIDE else solid, 0.5) * MM
            t_mm = tris_of(solid, 0.15)
            fine[part] = t_mm * MM
            grams[part] = V.MASS["motor"] if kind == "motor" else printed_grams(t_mm, kind == "tpu", part)
            print(f"  {part:15s} {len(fine[part]):6d} / {len(light[part]):5d} triangles  {grams[part]:6.1f} g")
        body = bodies[group_body["foot" + group[-1]] if part == "foot" else group_body[group]]
        place = inv(body.G) @ to_model(M)
        body.visuals.append((part, COLOUR[part], place))
        body.add_mass(grams[part], apply(place, fine[part]))

    base = bodies["base"]
    to_base = inv(base.G) @ to_model(np.eye(4))  # robot frame of the CAD (in metres) to the base frame
    for name, solid in V.electronics().items():
        base.add_mass(V.MASS[name], apply(to_base, tris_of(solid, 0.5) * MM))
        if name == "imu":  # the imu site sits in the middle of the motion sensor's board
            c = solid.val().BoundingBox().center
            base.imu = apply(to_base, np.array([[c.x, c.y, c.z]]) * MM)[0]
    total = sum(b.mass for b in bodies.values()) * 1000
    lump = max(0.0, LUMP - total)
    # screws, wires and cables: a slab over the deck
    slab = np.array(A.tess(A.part("deck"), 0.5, 0.5), dtype=np.float64).reshape(-1, 3, 3) * MM
    base.add_mass(lump, apply(to_base, slab))
    print(f"mass {sum(b.mass for b in bodies.values()) * 1000:.0f} g, of which {lump:.0f} g lumped on the deck")
    return F, bodies, fine, light


# ------------------------------------------------------------------ collision shapes, in body frames (metres)
def collisions():
    """(body, kind, params). Rough shapes: only feet are meant to touch the ground in normal walking."""
    c = []
    c.append(("base", "box", dict(size=(0.062, 0.065, 0.019), pos=(0, 0, (36 + 74.5) / 2 * MM - HIP_Z * MM))))
    c.append(("base", "box", dict(size=(0.069, 0.072, 0.0305), pos=(0, 0, (76.5 + 138) / 2 * MM - HIP_Z * MM))))
    for leg in LEG_NAMES:
        c.append((f"{leg}_thigh", "capsule", dict(fromto=(0.008, 0, 0, L1 * MM - 0.008, 0, 0), size=0.0125)))
        c.append((f"{leg}_shin", "capsule", dict(fromto=(0.01, 0, 0, 0.07, 0, 0), size=0.011)))
        c.append((f"{leg}_foot", "sphere", dict(size=FOOT_R * MM, pos=(0, 0, 0), foot=True)))
    c.append(("upper_arm", "capsule", dict(fromto=(0.01, 0, 0, LA * MM - 0.01, 0, 0), size=0.012)))
    c.append(("forearm", "capsule", dict(fromto=(0.01, 0, 0, 0.04, 0, 0), size=0.012)))
    c.append(("forearm", "box", dict(size=(0.013, 0.021, 0.0145), pos=(0.051, 0.002, 0))))
    c.append(("forearm", "box", dict(size=(0.0325, 0.00425, 0.01125), pos=(0.0885, -0.01575, -0.00325))))
    c.append(("finger", "box", dict(size=(0.015, 0.0045, 0.0105), pos=(0.032, 0.005, 0))))
    return c


def joints_for(body):
    """(joint name, axis in the body's frame, range) of the joint that moves this body."""
    if body.endswith("_hip"):
        return f"{body[:2]}_hip_turn", (0, 0, 1), RANGE["hip_turn"]
    if body.endswith("_thigh"):
        return f"{body[:2]}_hip_lift", (0, -1, 0), RANGE["hip_lift"]
    if body.endswith("_shin"):
        return f"{body[:2]}_knee", (0, 1, 0), RANGE["knee"]
    return {
        "upper_arm": ("arm_shoulder", (0, -1, 0), RANGE["arm_shoulder"]),
        "forearm": ("arm_elbow", (0, -1, 0), RANGE["arm_elbow"]),
        "finger": ("claw", (0, 0, 1), RANGE["claw"]),
    }.get(body)


PARENT = {"upper_arm": "base", "forearm": "upper_arm", "finger": "forearm"}
for _leg in LEG_NAMES:
    PARENT.update({f"{_leg}_hip": "base", f"{_leg}_thigh": f"{_leg}_hip", f"{_leg}_shin": f"{_leg}_thigh",
                   f"{_leg}_foot": f"{_leg}_shin"})
ORDER = [f"{leg}_{p}" for leg in LEG_NAMES for p in ("hip", "thigh", "shin", "foot")] + ["upper_arm", "forearm", "finger"]
JOINT_ORDER = [j for b in ORDER if (j := joints_for(b))]
STAND_Q = [STAND[n[3:]] if n[:2] in LEG_NAMES else ARM_STAND[n] for n, _, _ in JOINT_ORDER]


# ------------------------------------------------------------------ MJCF
def mjcf(bodies, mesh_names, skip=()):
    coll = collisions()
    lines = []
    w = lines.append
    w('<mujoco model="scorpion_spider">')
    w("  <!-- Generated by robot/build_model.py from the v0.5 CAD. Do not edit by hand. -->")
    w('  <compiler angle="radian" meshdir="meshes" autolimits="true"/>')
    w('  <option timestep="0.002" integrator="implicitfast"/>')
    w("  <default>")
    w('    <default class="scorpion">')
    w(f'      <joint damping="{MOTOR["damping"]}" armature="{MOTOR["armature"]}" frictionloss="{MOTOR["frictionloss"]}"/>')
    w(f'      <position kp="{MOTOR["kp"]}" kv="{MOTOR["kv"]}" forcerange="-{MOTOR["effort"]} {MOTOR["effort"]}"/>')
    w('      <default class="visual"><geom type="mesh" contype="0" conaffinity="0" group="2" density="0"/></default>')
    w('      <default class="collision"><geom contype="2" conaffinity="1" group="3" density="0" friction="0.9 0.02 0.001" rgba="0.5 0.6 0.9 0.4"/>')
    w('        <default class="foot"><geom type="sphere" friction="1.1 0.02 0.001" priority="1"/></default>')
    w("      </default>")
    w("    </default>")
    w("  </default>")
    w("  <asset>")
    for m, rgba in MATERIALS.items():
        extra = ' specular="0.9" shininess="0.9"' if m == "eye" else ' specular="0.3" shininess="0.4"'
        w(f'    <material name="{m}" rgba="{f(*rgba, nd=3)}"{extra}/>')
    for m in mesh_names:
        w(f'    <mesh name="{m}" file="{m}.stl"/>')
    w("  </asset>")
    w("  <worldbody>")

    def emit(name, depth):
        b = bodies[name]
        pad = "  " * depth
        if name == "base":
            w(f'{pad}<body name="base" pos="0 0 {BASE_HEIGHT:.4f}" childclass="scorpion">')
            w(f'{pad}  <freejoint name="root"/>')
        else:
            rel = inv(bodies[PARENT[name]].G) @ b.G
            w(f'{pad}<body name="{name}" pos="{f(*rel[:3, 3])}" quat="{f(*quat(rel[:3, :3]))}">')
            j = joints_for(name)
            if j:
                jn, axis, (lo, hi) = j
                w(f'{pad}  <joint name="{jn}" axis="{f(*axis)}" range="{f(lo, hi)}"/>')
        m, com, I = b.inertial()
        w(f'{pad}  <inertial pos="{f(*com)}" mass="{m:.5f}" fullinertia="{f(I[0,0], I[1,1], I[2,2], I[0,1], I[0,2], I[1,2], nd=9)}"/>')
        for mesh, mat, P in b.visuals:
            if mesh in skip:
                continue
            w(f'{pad}  <geom class="visual" mesh="{mesh}" material="{mat}" pos="{f(*P[:3, 3])}" quat="{f(*quat(P[:3, :3]))}"/>')
        for k, (bn, kind, p) in enumerate([c for c in coll if c[0] == name]):
            if p.get("foot"):
                w(f'{pad}  <geom name="{name}" class="foot" size="{f(p["size"])}"/>')
                continue
            attrs = f'type="{kind}" size="{f(*np.atleast_1d(p["size"]))}"'
            if "fromto" in p:
                attrs += f' fromto="{f(*p["fromto"])}"'
            if "pos" in p:
                attrs += f' pos="{f(*p["pos"])}"'
            w(f'{pad}  <geom name="{name}_collision{k}" class="collision" {attrs}/>')
        if name == "base":
            w(f'{pad}  <site name="imu" pos="{f(*b.imu)}"/>')
        if name == "forearm":
            w(f'{pad}  <site name="grip" pos="{f(LH * MM, 0, -0.00125)}" size="0.004"/>')
        for child in [c for c in ORDER if PARENT.get(c) == name]:
            emit(child, depth + 1)
        w(f"{pad}</body>")

    emit("base", 2)
    w("  </worldbody>")
    w("  <actuator>")
    for jn, _, (lo, hi) in JOINT_ORDER:
        w(f'    <position name="{jn}" joint="{jn}" class="scorpion" ctrlrange="{f(lo, hi)}"/>')
    w("  </actuator>")
    w("  <keyframe>")
    qpos = [0, 0, BASE_HEIGHT, 1, 0, 0, 0] + STAND_Q
    w(f'    <key name="stand" qpos="{f(*qpos)}" ctrl="{f(*STAND_Q)}"/>')
    w("  </keyframe>")
    w("</mujoco>")
    return "\n".join(lines) + "\n"


SCENE = """<mujoco model="scorpion_spider_scene">
  <!-- Generated by robot/build_model.py. The robot on a flat floor: python -m mujoco.viewer --mjcf robot/scorpion/scene.xml -->
  <include file="scorpion.xml"/>
  <statistic center="0 0 0.08" extent="0.4"/>
  <visual><global azimuth="140" elevation="-25"/></visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.1 0.12 0.13" rgb2="0.16 0.18 0.2" width="300" height="300"/>
    <material name="grid" texture="grid" texrepeat="40 40" reflectance="0.1"/>
  </asset>
  <worldbody>
    <light pos="0.3 -0.3 1.2" dir="-0.2 0.2 -1" directional="true"/>
    <geom name="floor" type="plane" size="5 5 0.05" material="grid" condim="3"/>
  </worldbody>
</mujoco>
"""


# ------------------------------------------------------------------ URDF
def urdf(bodies):
    coll = collisions()
    lines = ['<?xml version="1.0"?>', '<robot name="scorpion_spider">',
             "  <!-- Generated by robot/build_model.py from the v0.5 CAD. Do not edit by hand. -->"]
    w = lines.append
    for m, rgba in MATERIALS.items():
        w(f'  <material name="{m}"><color rgba="{f(*rgba, nd=3)}"/></material>')
    for name in ["base"] + ORDER:
        b = bodies[name]
        m, com, I = b.inertial()
        w(f'  <link name="{name}">')
        w(f'    <inertial><origin xyz="{f(*com)}" rpy="0 0 0"/><mass value="{m:.5f}"/>'
          f'<inertia ixx="{I[0,0]:.9f}" ixy="{I[0,1]:.9f}" ixz="{I[0,2]:.9f}" iyy="{I[1,1]:.9f}" iyz="{I[1,2]:.9f}" izz="{I[2,2]:.9f}"/></inertial>')
        for mesh, mat, P in b.visuals:
            w(f'    <visual><origin xyz="{f(*P[:3, 3])}" rpy="{f(*rpy(P[:3, :3]))}"/>'
              f'<geometry><mesh filename="meshes/{mesh}.stl"/></geometry><material name="{mat}"/></visual>')
        for bn, kind, p in [c for c in coll if c[0] == name]:
            if kind == "sphere":
                w(f'    <collision><origin xyz="{f(*p["pos"])}" rpy="0 0 0"/><geometry><sphere radius="{f(p["size"])}"/></geometry></collision>')
            elif kind == "box":
                w(f'    <collision><origin xyz="{f(*p["pos"])}" rpy="0 0 0"/><geometry><box size="{f(*(2 * np.array(p["size"])))}"/></geometry></collision>')
            else:  # capsule along x: URDF has no capsule, so a cylinder with the same length
                a, bb = np.array(p["fromto"][:3]), np.array(p["fromto"][3:])
                mid, ln = (a + bb) / 2, np.linalg.norm(bb - a) + 2 * p["size"]
                w(f'    <collision><origin xyz="{f(*mid)}" rpy="0 {f(math.pi / 2)} 0"/><geometry><cylinder radius="{f(p["size"])}" length="{f(ln)}"/></geometry></collision>')
        w("  </link>")
    for name in ORDER:
        rel = inv(bodies[PARENT[name]].G) @ bodies[name].G
        j = joints_for(name)
        if j:
            jn, axis, (lo, hi) = j
            w(f'  <joint name="{jn}" type="revolute"><parent link="{PARENT[name]}"/><child link="{name}"/>'
              f'<origin xyz="{f(*rel[:3, 3])}" rpy="{f(*rpy(rel[:3, :3]))}"/><axis xyz="{f(*axis)}"/>'
              f'<limit lower="{f(lo)}" upper="{f(hi)}" effort="{MOTOR["effort"]}" velocity="{MOTOR["velocity"]}"/>'
              f'<dynamics damping="{MOTOR["damping"]}" friction="{MOTOR["frictionloss"]}"/></joint>')
        else:
            w(f'  <joint name="{name}_fixed" type="fixed"><parent link="{PARENT[name]}"/><child link="{name}"/>'
              f'<origin xyz="{f(*rel[:3, 3])}" rpy="{f(*rpy(rel[:3, :3]))}"/></joint>')
    w("</robot>")
    return "\n".join(lines) + "\n"


def main():
    F, bodies, fine, light = build()
    names = sorted(fine)
    targets = [(OUT, fine, ()), (WEB, light, WEB_SKIP)] if HAS_WEB else [(OUT, fine, ())]
    for d, meshes, skip in targets:
        (d / "meshes").mkdir(parents=True, exist_ok=True)
        for old in (d / "meshes").glob("*.stl"):
            old.unlink()
        kept = [m for m in names if m not in skip]
        for m in kept:
            write_stl(d / "meshes" / f"{m}.stl", meshes[m])
        (d / "scorpion.xml").write_text(mjcf(bodies, kept, skip))
    (OUT / "scene.xml").write_text(SCENE)
    (OUT / "scorpion.urdf").write_text(urdf(bodies))
    info = dict(
        source="robot/cad (scorpion spider v0.5)",
        frame="x forward, y left, z up; metres, radians",
        joints=[dict(name=n, axis=a, lower=lo, upper=hi) for n, a, (lo, hi) in JOINT_ORDER],
        stand=dict(base_height=BASE_HEIGHT, joints=dict(zip([n for n, _, _ in JOINT_ORDER], STAND_Q))),
        motor=MOTOR,
        mass=sum(b.mass for b in bodies.values()),
        feet=[f"{leg}_foot" for leg in LEG_NAMES],
        foot_radius=FOOT_R * MM,
    )
    (OUT / "model.json").write_text(json.dumps(info, indent=2) + "\n")
    print("wrote", " and ".join(str(d.relative_to(ROOT)) for d, _, _ in targets))


if __name__ == "__main__":
    main()
