import sys, os, time, itertools, math, json
from assembly import *
from assembly import _bb, _bb_hit
from poses import *
P = named(); only = sys.argv[1:] or list(P)
D = math.degrees; summary = {}
for nm in only:
    Tb, q, ok = joints(P[nm]); t = time.time()
    g = world_solids(q)
    flat = [(n, s, _bb(s)) for grp in g.values() for n, s in grp]
    hits = []
    for (na, sa, ba), (nb, sb, bb_) in itertools.combinations(flat, 2):
        if not _bb_hit(ba, bb_) or press_fit(na, nb): continue
        v = overlap(sa, sb)
        if v > 0.5 or v < 0: hits.append((na, nb, round(v, 1)))
    # lowest point of anything but the feet, in the world
    low = 1e9; lown = ''
    for n, s, _ in flat:
        if n.startswith('foot'): continue
        z = place(s, Tb).val().BoundingBox().zmin
        if z < low: low, lown = z, n
    tip = tip_world(Tb, q)
    rng = dict(yaw=(D(min(q['yaw'])), D(max(q['yaw']))), lift=(D(min(q['lift'])), D(max(q['lift']))), knee=(D(min(q['knee'])), D(max(q['knee']))))
    summary[nm] = dict(ok=ok, hits=hits, low=round(low, 1), lown=lown, tip=[round(x, 1) for x in tip], a1=round(D(q['a1'])), elbow=round(D(q['a2'] - q['a1'])), **{k: [round(a), round(b)] for k, (a, b) in rng.items()})
    low -= FLOOR
    summary[nm]['low'] = round(low, 1)
    print(f"{nm:12s} reach_ok={ok} overlaps={hits if hits else 'none'}  lowest {low:5.1f} mm above floor ({lown})  tip {summary[nm]['tip']}  turn {summary[nm]['yaw']} lift {summary[nm]['lift']} knee {summary[nm]['knee']}  shoulder {summary[nm]['a1']} elbow {summary[nm]['elbow']}  {time.time()-t:.0f}s")
json.dump(summary, open(os.path.join(OUT_DIR, 'pose_check.json'), 'w'), indent=1)
