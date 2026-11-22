"""Data for a 3D viewer page: light meshes of every printed part and of the real motor, where everything sits, the joints, and the checked poses.
Writes out/view/meshes.json and out/view/scene.json. Not needed for printing."""
import sys, json, base64, math, pathlib
import numpy as np
from assembly import *
from assembly import _electronics
import vendor as V, body as B, poses as PS

OUT = pathlib.Path(OUT_DIR) / 'view'; OUT.mkdir(parents=True, exist_ok=True)
Q = 0.01                                             # mesh coordinates are int16 in units of 0.01 mm

def mesh_of(shape, tol, ang):
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float64); t = np.array(tris, dtype=np.int64)
    key = np.round(v / Q).astype(np.int64)             # weld points that land on the same grid cell
    uniq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
    t = inv[t]; t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    assert np.abs(uniq).max() < 32767, np.abs(uniq).max()
    it = t.astype(np.uint16 if len(uniq) < 65536 else np.uint32)
    return dict(n_verts=int(len(uniq)), n_tris=int(len(t)), index_bits=16 if len(uniq) < 65536 else 32,
                v=base64.b64encode(uniq.astype('<i2').tobytes()).decode(), i=base64.b64encode(it.astype('<u2' if len(uniq) < 65536 else '<u4').tobytes()).decode())

def one(wp): return wp.val() if len(wp.vals()) == 1 else cq.Compound.makeCompound(wp.vals())

meshes = {}
PRINTED = ['tub', 'battery_door', 'deck', 'hub_tray', 'shelf', 'lid', 'shoulder_mount', 'hip', 'thigh', 'shin', 'foot', 'upper_arm', 'forearm', 'palm_cap', 'finger', 'eye']
for n in PRINTED:
    fine = n in ('eye', 'foot', 'lid')
    meshes[n] = mesh_of(one(part(n)), 0.12 if fine else 0.25, 0.3 if fine else 0.5); print(n, meshes[n]['n_tris'])
# the real motor, split into the pieces a viewer will want to colour differently. Motor frame of parts.py.
real = V.motor_real()
if real is not None:
    sol = real.solids().vals()
    groups = dict(motor_case=[0, 4, 5], motor_horn=[7], motor_idler=[6], motor_gear=[1], motor_sockets=[2, 3], motor_screws=[8, 9, 10, 11, 12, 13])
    for g, idx in groups.items():
        meshes[g] = mesh_of(cq.Compound.makeCompound([sol[k] for k in idx]), 0.08 if g in ('motor_horn', 'motor_idler') else 0.15, 0.5); print(g, meshes[g]['n_tris'])
meshes['motor_simple'] = mesh_of(one(part('motor')), 0.25, 0.5)
json.dump(dict(unit_mm=Q, note='v = int16 little-endian xyz triples, multiply by unit_mm. i = triangle indices.', meshes=meshes), open(OUT / 'meshes.json', 'w'))

def M(m): return [round(float(x), 5) for x in np.array(m).reshape(-1)]          # row-major 4x4
def bb(s):
    b = s.val().BoundingBox() if len(s.vals()) == 1 else cq.Compound.makeCompound(s.vals()).BoundingBox()
    return [round(b.xmin, 2), round(b.ymin, 2), round(b.zmin, 2)], [round(b.xmax, 2), round(b.ymax, 2), round(b.zmax, 2)]

scene = dict(
    frame='Robot frame: X = right, Y = forward, Z = up, millimetres. Origin under the middle of the body at belly-floor level minus Z_BELLY; the floor is at z = FLOOR when standing.',
    matrix_layout='4x4 row-major: p_world = M @ [x, y, z, 1]',
    constants=dict(HIP_X=HIP_X, HIP_Y=HIP_Y, HIP_Z=HIP_Z, COXA=COXA, L1=L1, L2=L2, FOOT_R=FOOT_R, SH_Y=SH_Y, SH_Z=SH_Z, LA=LA, LH=LH, CLAW_X=CLAW_X, CLAW_Y=CLAW_Y,
                   FLOOR=FLOOR, Z_BELLY=Z_BELLY, Z_DECK=Z_DECK, Z_LIDBASE=Z_LIDBASE, Z_TOP=Z_TOP, BODY_X=BODY_X, BODY_Y=BODY_Y, FACE=FACE, HORN_T=HORN_T, LEGS=LEGS),
    kinematics=[
        "q = {yaw[4], lift[4], knee[4], a1, a2, grip}, radians. Legs i = 0..3 are LEGS[i] = (sx, sy): 0 front right, 1 front left, 2 back right, 3 back left.",
        "H_i = T(sx*HIP_X, sy*HIP_Y, HIP_Z) @ Rz(atan2(sy, sx))",
        "hip_i = H_i @ Rz(yaw_i)                       (turn joint: axis z of H_i)",
        "thigh_i = hip_i @ T(COXA,0,0) @ Ry(-lift_i)   (lift joint: axis y of hip_i at x = COXA)",
        "shin_i = thigh_i @ T(L1,0,0) @ Ry(pi - knee_i) (knee joint: axis y of thigh_i at x = L1; knee = angle between thigh and shin)",
        "foot_i = shin_i @ T(L2,0,0)",
        "upper_arm = T(0,SH_Y,SH_Z) @ Rz(pi/2) @ Ry(-a1)          (shoulder: axis x of the robot)",
        "forearm = upper_arm @ T(LA,0,0) @ Ry(-(a2 - a1))        (elbow: axis y of upper_arm at x = LA)",
        "finger = forearm @ T(CLAW_X,CLAW_Y,0) @ Rz(grip)        (claw: axis z of forearm)",
        "Motors ride on: turn motors, shoulder motor -> body. lift motor -> hip_i. knee motor -> thigh_i. elbow motor -> upper_arm. claw motor -> forearm.",
        "A pose also has a body matrix Tb (the body moves over fixed feet). World = Tb @ frame.",
    ],
    motor=dict(frame='origin on the shaft axis at mid-depth, Z = shaft, driven horn at +Z, idler horn at -Z, head (short) end at +Y, tail at -Y',
               case=[20.0, 34.0, 23.0], sockets=[dict(center=[6.9, -8.75, -FACE + 2.55], mouth_dir=[0, 0, -1]), dict(center=[-6.9, -8.75, -FACE + 2.55], mouth_dir=[0, 0, -1])]),
    instances=[dict(name=n, part=pn, kind=k, rides_on=g, matrix=M(m)) for n, pn, k, g, m in instances(REST)],
    rest=dict(q={k: (list(map(float, v)) if isinstance(v, list) else float(v)) for k, v in REST.items()}),
    electronics=[dict(name=n, min=bb(s)[0], max=bb(s)[1]) for n, s in _electronics().items()],
    deck_layout=dict(RADXA=B.RADXA, ADAPTER=B.ADAPTER, REG_B=B.REG_B, IMU=B.IMU, PASS=B.PASS, HUB=B.HUB, hub_z=B.HUB_Z, shelf_z=B.SHELF_Z, deck_top_z=Z_LIDBASE),
    openings=dict(switch=dict(center=[B.SWITCH[0], -BODY_Y, B.SWITCH[1]], r=B.SWITCH[2]),
                  speaker=dict(center=[0, -BODY_Y, B.SPK_Z]), camera=dict(center=[0, BODY_Y, CAM_Z]), battery_door=dict(half=list(B.BATT_OPEN), z=Z_BELLY)),
    poses={},
)
for nm, pose in PS.named().items():
    Tb, q, ok = PS.joints(pose)
    scene['poses'][nm] = dict(Tb=M(Tb), q={k: (list(map(float, v)) if isinstance(v, list) else float(v)) for k, v in q.items()}, reach_ok=bool(ok))
json.dump(scene, open(OUT / 'scene.json', 'w'), indent=1)
import os
print('meshes.json %.2f MB' % (os.path.getsize(OUT / 'meshes.json') / 1e6), ' scene.json %.0f kB' % (os.path.getsize(OUT / 'scene.json') / 1e3), ' total tris', sum(m['n_tris'] for m in meshes.values()))
