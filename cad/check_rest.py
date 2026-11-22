import sys, time, itertools
from assembly import *
from assembly import _bb, _bb_hit
q = dict(REST)
if len(sys.argv) > 1: q.update(eval(sys.argv[1]))
g = world_solids(q)
flat = [(n, s) for grp in g.values() for n, s in grp]
t = time.time(); hits = []
for (na, sa), (nb, sb) in itertools.combinations(flat, 2):
    if not _bb_hit(_bb(sa), _bb(sb)) or press_fit(na, nb): continue
    try: v = vol(sa.intersect(sb))
    except Exception as e: v = -1
    if v > 0.5 or v < 0: hits.append((na, nb, round(v, 1)))
print('pairs with overlap:', len(hits), 'time %.0fs' % (time.time() - t))
for h in sorted(hits, key=lambda h: -h[2]): print('  ', h)
