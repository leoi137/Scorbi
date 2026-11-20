"""Put the printed parts and the bought parts together at a pose. Kinematics match the checked page model."""
import math, json, base64, struct, sys, time
import numpy as np
import cadquery as cq
from prim import *
import parts as P, body as B, vendor as V
from parts import *

_cache = {}
def part(name):
    if name not in _cache:
        fn = getattr(P, name, None) or getattr(B, name, None) or getattr(V, name)
        _cache[name] = fn()
    return _cache[name]

def stand_angles(reach=FOOT_REACH, drop=HIP_Z - FOOT_R):
    """Hip lift angle and knee angle (between thigh and shin) that put the foot 'reach' out and 'drop' down from the lift axis."""
    D = math.hypot(reach, drop)
    e = math.atan2(-drop, reach) + math.acos((L1 * L1 + D * D - L2 * L2) / (2 * L1 * D))
    k = math.acos((L1 * L1 + L2 * L2 - D * D) / (2 * L1 * L2))
    return e, k

E0, K0 = stand_angles(drop=HIP_Z - FOOT_R + 10.0)
REST = dict(yaw=[0, 0, 0, 0], lift=[E0] * 4, knee=[K0] * 4, a1=1.25, a2=-0.55, grip=math.radians(-25))
CY, Y0 = 87.0, -13.5             # body centre height; the body stands 13.5 mm back from the middle of its feet (the arm is in front)
STAND_UP = 10.0                  # the real knee cannot fold below 22 degrees, so it stands 10 mm taller than the checked model
FLOOR = -STAND_UP                # floor height in body coordinates when standing
FOOT_HOME = [(sx * (HIP_X + (COXA + FOOT_REACH) * N45), sy * (HIP_Y + (COXA + FOOT_REACH) * N45), FLOOR + FOOT_R) for sx, sy in LEGS]

def body_T(yaw=0.0, pitch=0.0, x=0.0, y=0.0, z=0.0, roll=0.0):
    """Body pose over fixed feet: shift, turn about the middle, bow forward by 'pitch' about the front hip line (the back end rises)."""
    bow = T(0, HIP_Y, HIP_Z) @ Rx(-pitch) @ T(0, -HIP_Y, -HIP_Z)
    return T(x, Y0 + y, z) @ Rz(yaw) @ bow @ T(0, 0, CY) @ Ry(roll) @ T(0, 0, -CY)

def solve(Tb, arm=(1.25, -0.55), grip=math.radians(-25), feet=None, lift=(0, 0, 0, 0)):
    """Joint values that keep the feet where they are while the body sits at Tb. Returns (q, ok)."""
    q = dict(yaw=[], lift=[], knee=[], a1=arm[0], a2=arm[1], grip=grip); ok = True
    inv = np.linalg.inv(Tb)
    for i, (sx, sy) in enumerate(LEGS):
        F = np.array((feet or FOOT_HOME)[i], float) + (0, 0, lift[i])
        v = (inv @ np.append(F, 1.0))[:3] - (sx * HIP_X, sy * HIP_Y, HIP_Z)
        psi = math.atan2(v[1], v[0]) - math.atan2(sy, sx)
        psi = (psi + math.pi) % (2 * math.pi) - math.pi
        rho, drop = math.hypot(v[0], v[1]) - COXA, -v[2]
        D = math.hypot(rho, drop)
        if not (abs(L1 - L2) + 1 < D < L1 + L2 - 1): ok = False; D = min(max(D, abs(L1 - L2) + 1), L1 + L2 - 1)
        e = math.atan2(-drop, rho) + math.acos((L1 * L1 + D * D - L2 * L2) / (2 * L1 * D))
        k = math.acos((L1 * L1 + L2 * L2 - D * D) / (2 * L1 * L2))
        q['yaw'].append(psi); q['lift'].append(e); q['knee'].append(k)
    return q, ok

M_TURN = frame((0, 0, 0), (0, 1, 0), (1, 0, 0))                 # in the hip frame: shaft down, head out along the diagonal
M_LIFT = frame((COXA, 0, 0), (-1, 0, 0), (0, 0, 1))            # in the hip-bracket frame: shaft across, head up
def M_END(L): return frame((L, 0, 0), (0, 0, 1), (1, 0, 0))    # in a link frame: shaft across, head at the far end
M_SHOULDER = frame((0, SH_Y, SH_Z), (0, 0, -1), (0, 1, 0))
M_CLAW = frame((CLAW_X, CLAW_Y, 0), (0, -1, 0), (1, 0, 0))

def frames(q):
    """All link frames (4x4, robot frame) for joint values q."""
    f = {'body': np.eye(4), 'shoulder_mount': T(0, SH_Y, SH_Z)}
    for i, (sx, sy) in enumerate(LEGS):
        H = hip_frame(sx, sy)
        f[f'turn{i}'] = H @ M_TURN
        f[f'hip{i}'] = H @ Rz(q['yaw'][i])
        f[f'thigh{i}'] = f[f'hip{i}'] @ T(COXA, 0, 0) @ Ry(-q['lift'][i])
        f[f'shin{i}'] = f[f'thigh{i}'] @ T(L1, 0, 0) @ Ry(math.pi - q['knee'][i])
        f[f'foot{i}'] = f[f'shin{i}'] @ T(L2, 0, 0)
    f['upper_arm'] = T(0, SH_Y, SH_Z) @ Rz(math.pi / 2) @ Ry(-q['a1'])
    f['forearm'] = f['upper_arm'] @ T(LA, 0, 0) @ Ry(-(q['a2'] - q['a1']))
    f['finger'] = f['forearm'] @ T(CLAW_X, CLAW_Y, 0) @ Rz(q['grip'])
    return f

def instances(q):
    """List of (instance name, part name, kind, group, 4x4). kind: 'print', 'motor' or 'bought'. group = rigid body it rides on."""
    f = frames(q); out = []
    for n in ('tub', 'battery_door', 'deck', 'lid'):
        out.append((n, n, 'print', 'body', f['body']))
    out.append(('shoulder_mount', 'shoulder_mount', 'print', 'body', f['shoulder_mount']))
    for s in (1, -1):
        tag = "R" if s > 0 else "L"
        out.append((f'eye{tag}', 'eye', 'eye', 'body', panel_frame(s, EYE_Z)))
    out.append(('m_shoulder', 'motor', 'motor', 'body', M_SHOULDER))
    for i in range(4):
        out.append((f'm_turn{i}', 'motor', 'motor', 'body', f[f'turn{i}']))
        out.append((f'hip{i}', 'hip', 'print', f'hip{i}', f[f'hip{i}']))
        out.append((f'm_lift{i}', 'motor', 'motor', f'hip{i}', f[f'hip{i}'] @ M_LIFT))
        out.append((f'thigh{i}', 'thigh', 'print', f'thigh{i}', f[f'thigh{i}']))
        out.append((f'm_knee{i}', 'motor', 'motor', f'thigh{i}', f[f'thigh{i}'] @ M_END(L1)))
        out.append((f'shin{i}', 'shin', 'print', f'shin{i}', f[f'shin{i}']))
        out.append((f'foot{i}', 'foot', 'tpu', f'shin{i}', f[f'foot{i}']))
    out.append(('upper_arm', 'upper_arm', 'print', 'upper_arm', f['upper_arm']))
    out.append(('m_elbow', 'motor', 'motor', 'upper_arm', f['upper_arm'] @ M_END(LA)))
    out.append(('forearm', 'forearm', 'print', 'forearm', f['forearm']))
    out.append(('palm_cap', 'palm_cap', 'print', 'forearm', f['forearm']))
    out.append(('m_claw', 'motor', 'motor', 'forearm', f['forearm'] @ M_CLAW))
    out.append(('finger', 'finger', 'print', 'finger', f['finger']))
    return out

def world_solids(q, with_bought=True):
    """group -> list of (instance name, placed solid)."""
    g = {}
    for name, pn, kind, grp, M in instances(q):
        g.setdefault(grp, []).append((name, place(part(pn), M)))
    if with_bought:
        for n, s in _electronics().items():
            g['body'].append((n, s))
    return g

def _electronics():
    if 'electronics' not in _cache:
        _cache['electronics'] = V.electronics()
    return _cache['electronics']

def _bb(s):
    b = s.val().BoundingBox(); return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)
def _bb_hit(a, b, m=0.0):
    return a[0] < b[1] - m and b[0] < a[1] - m and a[2] < b[3] - m and b[2] < a[3] - m and a[4] < b[5] - m and b[4] < a[5] - m

def overlap(sa, sb):
    """Overlap volume of two solids. A boolean that returns a whole part as the overlap is re-checked by measuring the gap."""
    try:
        v = vol(sa.intersect(sb))
    except Exception:
        v = -1.0
    if v < 0 or v > 0.5 * min(vol(sa), vol(sb)):
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape
        gap = BRepExtrema_DistShapeShape(sa.val().wrapped, sb.val().wrapped).Value()
        if gap > 0.05: return 0.0
    return v

def clashes(ga, gb, tol=0.5):
    """Overlap volume (mm3) between every solid of group list ga and every solid of gb, above tol."""
    out = []
    for na, sa in ga:
        ba = _bb(sa)
        for nb, sb in gb:
            if not _bb_hit(ba, _bb(sb)):
                continue
            v = overlap(sa, sb)
            if v > tol or v < 0:
                out.append((na, nb, round(v, 1)))
    return out

# ---------------------------------------------------------------- meshes for the viewer and for STL files
def tess(solid, tol=0.25, ang=0.35):
    """Triangles of a solid as a flat float32 array (9 numbers per triangle)."""
    verts, tris = solid.val().tessellate(tol, ang) if len(solid.vals()) == 1 else cq.Compound.makeCompound(solid.vals()).tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float32)
    return v[np.array(tris, dtype=np.int32)].reshape(-1, 9)

def write_stl(path, tris):
    t = np.round(tris.reshape(-1, 3, 3).astype(np.float64), 4)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-9; t, n, ln = t[keep], n[keep], ln[keep]; n = n / ln[:, None]      # drop zero-area triangles (poles of revolved parts)
    with open(path, 'wb') as f:
        f.write(b'scorpion spider v0.4'.ljust(80, b' ')); f.write(struct.pack('<I', len(t)))
        for i in range(len(t)):
            f.write(struct.pack('<12fH', *n[i], *t[i].reshape(-1), 0))

def mesh_mass_props(tris):
    """Volume (mm3), centroid, surface area (mm2) of a closed triangle mesh."""
    t = tris.reshape(-1, 3, 3).astype(np.float64)
    cr = np.cross(t[:, 1], t[:, 2]); v6 = np.einsum('ij,ij->i', t[:, 0], cr)
    V = v6.sum() / 6.0
    c = ((t[:, 0] + t[:, 1] + t[:, 2]) * v6[:, None]).sum(axis=0) / (24.0 * V)
    A = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum()
    return V, c, A
