"""Export every printed part in its print orientation (STL + STEP), with print notes, mass and overhang figures."""
import sys, os, json, math, pathlib, time
import numpy as np
from assembly import *

OUT = pathlib.Path(OUT_DIR) / 'pack'
# name: (count, material, orientation matrix from part frame to print frame (before dropping to the bed), note)
# v0.5: PETG for every part that holds a motor (plain PLA can soften at 60 C). Settings in build-pack/, "Print guide".
PRINT = {
    'test_piece':     (1, 'PETG, any colour', np.eye(4), 'Flat base down. No supports. Print this first and do tests A1 to A7.'),
    'hip':            (4, 'PETG, coral', Rx(math.pi / 2), 'On its side. Supports only under the upper wall of the motor pocket. 4 walls, 5 mm brim.'),
    'thigh':          (4, 'PETG, cream', Ry(math.pi / 2), 'Standing on its open end, fork up. Supports: build plate only. 4 walls, 8 mm brim.'),
    'shin':           (4, 'PETG, cream', Ry(-math.pi / 2), 'Standing on its heel, foot peg up. No supports. 4 walls, 8 mm brim.'),
    'foot':           (4, 'TPU 95A, mint', Ry(-math.pi / 2), 'Flat face down. No supports. 30% infill.'),
    'tub':            (1, 'PETG, coral', np.eye(4), 'Belly down. Supports: build plate only, under the two bars.'),
    'deck':           (1, 'PETG, coral', np.eye(4), 'Flat side down, posts up. No supports.'),
    'battery_door':   (1, 'PETG, coral', np.eye(4), 'Flat plate down. No supports.'),
    'hub_tray':       (1, 'PETG, coral', np.eye(4), 'Flat plate down, walls up. No supports.'),
    'shelf':          (1, 'PETG, coral', np.eye(4), 'Flat plate down, rim up. No supports.'),
    'lid':            (1, 'PLA or PETG, cream', Rx(math.pi), 'Roof down. No supports. Slow the first 10 mm of the 45 degree edge.'),
    'shoulder_mount': (1, 'PETG, cream', np.eye(4), 'Base down. Supports everywhere. 4 walls.'),
    'upper_arm':      (1, 'PETG, cream', Ry(math.pi / 2), 'Standing on its open end, fork up. Supports: build plate only. 4 walls, 8 mm brim.'),
    'forearm':        (1, 'PETG, cream', np.eye(4), 'Flat side down. No supports. 4 walls.'),
    'palm_cap':       (1, 'PETG, coral', np.eye(4), 'Flat. No supports.'),
    'finger':         (1, 'PETG, mint', Rx(-math.pi / 2), 'On its side, blade down. No supports. 4 walls.'),
    'eye':            (2, 'PLA, glossy black', np.eye(4), 'Flat side down. No supports.'),
}
FOUR_WALLS = {'hip', 'thigh', 'shin', 'shoulder_mount', 'upper_arm', 'forearm', 'finger'}   # parts that carry a leg or arm load
WALL4 = 1.15                           # their extra plastic for the fourth wall
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
    grams = rho * (skin + infill * (V - skin)) / 1000 * (WALL4 if name in FOUR_WALLS else 1.0)
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
