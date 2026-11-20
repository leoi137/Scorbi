"""Export every printed part in its print orientation (STL + STEP), with print notes, mass and overhang figures."""
import sys, os, json, math, pathlib, time
import numpy as np
from assembly import *

OUT = pathlib.Path(OUT_DIR) / 'pack'
# name: (count, material, orientation matrix from part frame to print frame (before dropping to the bed), note)
PRINT = {
    'tub':            (1, 'PETG or PLA+, coral', np.eye(4), 'Belly down. No supports.'),
    'deck':           (1, 'PETG or PLA+, coral', np.eye(4), 'Flat side down. No supports.'),
    'battery_door':   (1, 'PETG or PLA+, coral', np.eye(4), 'Plate down. No supports.'),
    'lid':            (1, 'PLA, cream', Rx(math.pi), 'Roof down. No supports. Slow the first layers of the 45 degree edge.'),
    'shoulder_mount': (1, 'PETG or PLA+, cream', np.eye(4), 'Base down. The small hood bridges across. No supports.'),
    'hip':            (4, 'PETG or PLA+, coral', Rx(math.pi / 2), 'On its side. Supports only under the upper cheek of the motor pocket.'),
    'thigh':          (4, 'PETG, cream', Ry(math.pi / 2), 'Standing on its open end, fork up. 5 mm brim, 4 walls. No supports.'),
    'shin':           (4, 'PETG, cream', Ry(-math.pi / 2), 'Standing on its heel, foot peg up. 5 mm brim, 4 walls. No supports.'),
    'foot':           (4, 'TPU 95A, mint', Ry(-math.pi / 2), 'Flat face down. No supports. 100% infill is not needed: 30%.'),
    'upper_arm':      (1, 'PETG, cream', Ry(math.pi / 2), 'Standing on its open end, fork up. 5 mm brim, 4 walls. No supports.'),
    'forearm':        (1, 'PETG or PLA+, cream', np.eye(4), 'Flat side down. No supports.'),
    'palm_cap':       (1, 'PETG or PLA+, coral', np.eye(4), 'Flat. No supports.'),
    'finger':         (1, 'PETG or PLA+, mint', Rx(-math.pi / 2), 'On its side, blade down. No supports.'),
    'eye':            (2, 'PLA, glossy black', np.eye(4), 'Flat side down. No supports.'),
}
RHO = dict(default=1.24, tpu=1.21)     # g/cm3
SKIN, INFILL = 1.2, 0.15               # every surface gets 1.2 mm of solid skin, the rest is 15% full

def printed(name):
    cnt, mat, M, note = PRINT[name]
    s = place(part(name), M)
    b = s.val().BoundingBox()
    s = place(s, T(-(b.xmin + b.xmax) / 2, -(b.ymin + b.ymax) / 2, -b.zmin))
    return s

def analyse(name):
    cnt, mat, M, note = PRINT[name]
    s = printed(name); tris = tess(s, 0.1, 0.25)
    V, c, A = mesh_mass_props(tris)
    t = tris.reshape(-1, 3, 3).astype(float)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); ar = 0.5 * np.linalg.norm(n, axis=1); nz = n[:, 2] / np.maximum(2 * ar, 1e-12)
    zc = t[:, :, 2].mean(axis=1)
    over = ar[(nz < -0.72) & (zc > 0.3)].sum()                       # faces that look down, above the first layer
    ext = t.reshape(-1, 3).max(axis=0) - t.reshape(-1, 3).min(axis=0)
    rho = RHO['tpu'] if 'TPU' in mat else RHO['default']
    skin = min(V, A * SKIN); infill = 0.30 if 'TPU' in mat else INFILL
    grams = rho * (skin + infill * (V - skin)) / 1000
    return dict(name=name, count=cnt, material=mat, note=note, size=[round(float(x), 1) for x in ext], volume_cm3=round(V / 1000, 2),
                grams=round(grams, 1), solid_grams=round(rho * V / 1000, 1), overhang_cm2=round(over / 100, 1)), s, tris

if __name__ == '__main__':
    (OUT / 'stl').mkdir(parents=True, exist_ok=True); (OUT / 'step').mkdir(parents=True, exist_ok=True)
    rows = []
    for name in PRINT:
        info, s, tris = analyse(name); rows.append(info)
        if '--files' in sys.argv:
            write_stl(str(OUT / 'stl' / f"{name}_x{info['count']}.stl"), tris)
            cq.exporters.export(s, str(OUT / 'step' / f"{name}.step"))
        print(f"{name:15s} x{info['count']}  {info['size']}  {info['grams']:6.1f} g each (solid {info['solid_grams']:6.1f})  looks-down area {info['overhang_cm2']:5.1f} cm2")
    tot = sum(r['grams'] * r['count'] for r in rows)
    print('printed total g', round(tot, 1), ' solid', round(sum(r['solid_grams'] * r['count'] for r in rows), 1))
    json.dump(rows, open(os.path.join(OUT_DIR, 'print_table.json'), 'w'), indent=1)
