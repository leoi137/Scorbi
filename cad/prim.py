"""Small solid-modelling helpers on top of CadQuery. All dimensions in millimetres."""
import math, os
import numpy as np
import cadquery as cq

# where the scripts write: set SPIDER_OUT, or they use an "out" folder next to this "source" folder
OUT_DIR = os.environ.get('SPIDER_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
os.makedirs(os.path.join(OUT_DIR, 'pack', 'stl'), exist_ok=True); os.makedirs(os.path.join(OUT_DIR, 'pack', 'step'), exist_ok=True)

def box(x0, x1, y0, y1, z0, z1):
    assert x1 > x0 and y1 > y0 and z1 > z0, (x0, x1, y0, y1, z0, z1)
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl(axis, a, b, r, lo, hi):
    """Cylinder along 'x', 'y' or 'z' from lo to hi. (a, b) are the two other coordinates in x<y<z order."""
    c = cq.Workplane("XY").circle(r).extrude(hi - lo).translate((0, 0, lo))
    if axis == 'z':
        return c.translate((a, b, 0))
    if axis == 'y':                       # z -> y
        return c.rotate((0, 0, 0), (1, 0, 0), -90).translate((a, 0, b))
    if axis == 'x':                       # z -> x
        return c.rotate((0, 0, 0), (0, 1, 0), 90).translate((0, a, b))
    raise ValueError(axis)

def cone(axis, a, b, r0, r1, lo, hi):
    """Cone/frustum along an axis: radius r0 at lo, r1 at hi."""
    s = cq.Workplane("XY").add(cq.Solid.makeCone(r0, r1, hi - lo, cq.Vector(0, 0, lo), cq.Vector(0, 0, 1)))
    if axis == 'z':
        return s.translate((a, b, 0))
    if axis == 'y':
        return s.rotate((0, 0, 0), (1, 0, 0), -90).translate((a, 0, b))
    if axis == 'x':
        return s.rotate((0, 0, 0), (0, 1, 0), 90).translate((0, a, b))
    raise ValueError(axis)

def union(*parts):
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out.clean()

def cut(base, *tools):
    for t in tools:
        base = base.cut(t)
    return base

def vol(wp):
    return sum(s.Volume() for s in wp.solids().vals())

def bbox(wp):
    b = wp.val().BoundingBox() if len(wp.vals()) == 1 else cq.Compound.makeCompound(wp.vals()).BoundingBox()
    return (round(b.xmin, 2), round(b.xmax, 2), round(b.ymin, 2), round(b.ymax, 2), round(b.zmin, 2), round(b.zmax, 2))

# ---- rigid transforms as 4x4 numpy matrices ----
def T(x=0, y=0, z=0):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m
def Rx(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4); m[1, 1], m[1, 2], m[2, 1], m[2, 2] = c, -s, s, c; return m
def Ry(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4); m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c; return m
def Rz(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4); m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c; return m
def frame(origin, xdir, ydir):
    """4x4 frame from an origin and two orthogonal unit directions (z = x cross y)."""
    x = np.array(xdir, float); x /= np.linalg.norm(x); y = np.array(ydir, float); y /= np.linalg.norm(y)
    assert abs(x @ y) < 1e-9
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, np.cross(x, y), origin; return m

def place(wp, M):
    """Return the solid(s) of a workplane moved by a rigid 4x4 matrix."""
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf()
    t.SetValues(*[float(M[i][j]) for i in range(3) for j in range(4)])
    shapes = [cq.Shape.cast(BRepBuilderAPI_Transform(s.wrapped, t, True).Shape()) for s in wp.vals()]
    return cq.Workplane("XY").newObject(shapes)

# ---- rounded features ----
def _orient(c, axis, a, b):
    if axis == 'z': return c.translate((a, b, 0))
    if axis == 'y': return c.rotate((0, 0, 0), (1, 0, 0), -90).translate((a, 0, b))
    if axis == 'x': return c.rotate((0, 0, 0), (0, 1, 0), 90).translate((0, a, b))
    raise ValueError(axis)

def lens(axis, a, b, face, s, r, h):
    """Shallow dome of height h on a disc of radius r. It sits on the plane 'face' along the axis and bulges toward s (+1 or -1)."""
    rho = (r * r + h * h) / (2 * h)
    sph = cq.Workplane("XY").sphere(rho).translate((0, 0, face + s * (h - rho)))
    lo, hi = sorted((face - s * 0.6, face + s * (h + 0.5)))                # rooted 0.6 mm inside the disc, so the join is clean
    return _orient(sph.intersect(cq.Workplane("XY").circle(r).extrude(hi - lo).translate((0, 0, lo))), axis, a, b)

def sector(R, a0, a1, y0, y1, r_in=0.0):
    """Pie slice (or ring slice) about the y axis: angles in degrees measured from +x toward +z, between y0 and y1."""
    import math as _m
    am = (a0 + a1) / 2
    P = lambda a, rr=R: (rr * _m.cos(_m.radians(a)), rr * _m.sin(_m.radians(a)))
    w = cq.Workplane("XY").moveTo(0, 0).lineTo(*P(a0)).threePointArc(P(am), P(a1)).close().extrude(y1 - y0)
    w = w.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, y1, 0))          # sketch (u, v) -> (x, z); thickness -> y
    if r_in > 0: w = w.cut(cyl('y', 0, 0, r_in, y0 - 1, y1 + 1))
    return w

def arch(axis, half, base, rise, lo, hi):
    """Bulged strip: a circular-segment profile (chord 2*half at height 'base', rising by 'rise'), swept from lo to hi.
    axis 'x': profile in (y, z). axis 'y': profile in (x, z)."""
    prof = cq.Workplane("XY").moveTo(-half, base).lineTo(half, base).threePointArc((0, base + rise), (-half, base)).close().extrude(hi - lo)
    if axis == 'x':   # sketch (u, v, w) -> (w, u, v)
        return prof.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90).translate((lo, 0, 0)) if False else _arch_x(prof, lo)
    if axis == 'y':   # sketch (u, v, w) -> (u, -w, v), then shift so it spans lo..hi
        return prof.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, hi, 0))
    raise ValueError(axis)

def _arch_x(prof, lo):
    # (u, v, w): rotate about x by 90 -> (u, -w, v); rotate about z by -90 -> (y', x') = ... result (x, y, z) = (-(-w), ... )
    p = prof.rotate((0, 0, 0), (1, 0, 0), 90)          # (u, -w, v)
    p = p.rotate((0, 0, 0), (0, 0, 1), 90)             # (x, y) -> (-y, x): (w, u, v)
    return p.translate((lo, 0, 0))
