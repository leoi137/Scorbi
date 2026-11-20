"""Find the collision-free range of every joint by sweeping it and intersecting the solids."""
import sys, time, math, json
from assembly import *
D = math.radians
def groups(q): return world_solids(q)
def test(q, ga, gb):
    g = groups(q); A = [x for n in ga for x in g[n]]; B = [x for n in gb for x in g[n]]
    return clashes(A, B)
def sweep(label, key, idx, vals, ga, gb, base=None):
    res = []
    for v in vals:
        q = {k: (list(x) if isinstance(x, list) else x) for k, x in (base or REST).items()}
        if idx is None: q[key] = D(v)
        else: q[key][idx] = D(v)
        h = test(q, ga, gb); res.append((v, h))
    ok = [v for v, h in res if not h]
    print(f"{label}: clear at {ok}")
    for v, h in res:
        if h: print(f"     {v:>5}: " + ', '.join(f"{a}x{b}={c}" for a, b, c in h[:4]))
    return res
t = time.time(); i = 0
body = ['body']
sweep('hip turn, bracket vs body', 'yaw', i, [-60, -50, -45, -35, 0, 35, 45, 50, 60], [f'hip{i}'], body)
sweep('hip lift, thigh vs hip bracket', 'lift', i, [-30, -15, 0, 15, 30, 56, 80, 95, 100, 105, 110], [f'thigh{i}'], [f'hip{i}'])
sweep('hip lift, thigh vs body (yaw 0)', 'lift', i, [56, 80, 90, 95, 100, 110], [f'thigh{i}'], body)
sweep('knee, shin vs thigh', 'knee', i, [15, 18, 20, 22, 25, 30, 36, 60, 90, 100, 105, 110, 120], [f'shin{i}'], [f'thigh{i}'])
sweep('knee, shin vs hip bracket (lift at rest)', 'knee', i, [15, 18, 20, 22, 25, 30, 36, 60], [f'shin{i}'], [f'hip{i}'])
sweep('knee, shin vs body (lift at rest)', 'knee', i, [15, 20, 25, 30, 36], [f'shin{i}'], body)
print('--- arm')
sweep('shoulder, upper arm vs body', 'a1', None, [-5, 0, 5, 11, 72, 90, 95, 100, 105, 110], ['upper_arm'], body)
def elbow(v): return v
for a1 in (11, 72, 100):
    base = dict(REST); base['a1'] = D(a1)
    res = []
    for rel in [0, -20, -60, -100, -110, -120, -130, -140]:
        q = dict(base); q['a2'] = D(a1 + rel)
        h = test(q, ['forearm', 'finger'], ['upper_arm']); h2 = test(q, ['forearm', 'finger'], body)
        res.append((rel, h, h2))
    print(f"elbow at shoulder {a1}: clear vs upper arm {[r for r, h, _ in res if not h]}, clear vs body {[r for r, _, h in res if not h]}")
    for r, h, h2 in res:
        if h or h2: print(f"     {r:>5}: " + ', '.join(f"{a}x{b}={c}" for a, b, c in (h + h2)[:4]))
sweep('claw, finger vs forearm', 'grip', None, [-40, -35, -28, -15, 0, 15, 30, 40, 50], ['finger'], ['forearm'])
print('time %.0fs' % (time.time() - t))
