"""Named poses from the checked motion clips, turned into joint values for the CAD."""
import math
import numpy as np
from assembly import *

BOW, DIP, YAW = 0.32, -14.0, 0.10
ARM = dict(rest=(1.25, -0.55), high=(1.45, 0.10), carry=(1.60, -0.20), out=(0.2, 0.2))
G_OPEN, G_HOLD, G_SHUT = math.radians(26), 0.0, math.radians(-25)

def tip_world(Tb, q):
    return (Tb @ frames(q)['forearm'] @ np.array([LH, 0, 0, 1.0]))[:3]

def down_arm(Tb, a1=0.0, target=FLOOR + 12.5):
    """Hand angle that puts the grip centre at block height while the body bows."""
    lo, hi = -1.57, 0.2
    for _ in range(40):
        mid = (lo + hi) / 2; q, _ok = solve(Tb, (a1, mid))
        if tip_world(Tb, q)[2] > target: hi = mid
        else: lo = mid
    return (a1, (lo + hi) / 2)

def named():
    P = {}
    P['stand'] = (body_T(), ARM['rest'], G_SHUT, None)
    for s, nm in ((1, 'reach_left'), (-1, 'reach_right')):
        Tb = body_T(yaw=s * YAW, pitch=BOW, z=DIP)
        P[nm] = (Tb, down_arm(Tb), G_OPEN, None)
    Tb = body_T(pitch=BOW, z=DIP); P['reach_front'] = (Tb, down_arm(Tb), G_HOLD, None)
    P['hold_high'] = (body_T(), ARM['high'], G_HOLD, None)
    P['carry'] = (body_T(), ARM['carry'], G_HOLD, None)
    P['arm_out'] = (body_T(), ARM['out'], G_HOLD, None)
    # walk: body leans 33 mm to the side and 24 mm fore/aft; one foot 15 mm up; feet up to 18 mm ahead or behind
    for k, (bx, by, leg, dy) in enumerate([(-23, 30, 2, 0), (-33, -10, 0, 0), (23, 30, 3, 0), (33, -18, 1, 0), (-33, 30, 0, 18), (33, 30, 1, -18)]):
        feet = [list(f) for f in FOOT_HOME]
        for i in range(4): feet[i][1] += (18 if i % 2 == 0 else -18) * (1 if k % 2 == 0 else -1)
        feet[leg][1] += dy; lift = [0, 0, 0, 0]; lift[leg] = 15
        P[f'walk{k}'] = (body_T(x=bx, y=by, z=-1.5, roll=0.03 * (1 if bx > 0 else -1)), ARM['carry'], G_HOLD, (feet, lift))
    P['dance_a'] = (body_T(yaw=0.16, x=-9, z=-7.5, roll=0.06), (1.57, 0.05), G_OPEN, None)
    P['dance_b'] = (body_T(yaw=-0.16, x=9, z=0, roll=-0.06), (1.13, -0.75), G_SHUT, None)
    # sitting: belly on the floor, feet stepped 45 mm further out
    feet = [(f[0] + s[0] * 45 * N45, f[1] + s[1] * 45 * N45, f[2]) for f, s in zip(FOOT_HOME, LEGS)]
    P['sit'] = (body_T(y=-Y0, z=FLOOR - Z_BELLY + 0.5), ARM['rest'], G_SHUT, (feet, [0, 0, 0, 0]))
    return P

def joints(pose):
    Tb, arm, grip, extra = pose
    feet, lift = extra if extra else (None, (0, 0, 0, 0))
    q, ok = solve(Tb, arm, grip, feet, lift)
    return Tb, q, ok
