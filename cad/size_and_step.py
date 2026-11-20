"""Overall size standing, and one STEP file of the whole robot standing with motors and boards."""
import json, sys, os
from assembly import *
g = world_solids(REST)
solids = [s for grp in g.values() for _n, s in grp]
lo = np.array([1e9] * 3); hi = -lo
for s in solids:
    b = s.val().BoundingBox(); lo = np.minimum(lo, (b.xmin, b.ymin, b.zmin)); hi = np.maximum(hi, (b.xmax, b.ymax, b.zmax))
size = [round(float(x)) for x in (hi - lo)]
json.dump(dict(size=size), open(os.path.join(OUT_DIR, 'size.json'), 'w')); print('size', size)
if '--step' in sys.argv:
    comp = cq.Compound.makeCompound([v for s in solids for v in s.vals()])
    cq.exporters.export(cq.Workplane(obj=comp), os.path.join(OUT_DIR, 'pack', 'step', '_assembly_standing.step')); print('wrote assembly step')
