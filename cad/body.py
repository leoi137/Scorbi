"""Body of the scorpion spider v0.5: rounded chassis, battery door, deck, hub tray, fuse shelf, pebble head shell, eyes.
Robot frame, millimetres.

What changed from v0.4 (build-pack/, "Findings"): a ready-made 2S pack in a longer bay, charged outside the robot, so the
charge board, its shelf and its USB-C hole are gone; the battery door is held by flat-head M3 screws into captive nuts;
eight more deck screws beside the hips; a new deck layout, with the camera rails, a hub tray of lever connectors and a
fuse shelf on it; captive nuts for the head-shell screws; and a toggle switch with a battery rating on the back.
"""
import math
from prim import *
from parts import *

SQ = math.sqrt(2) - 1

def octagon(inset=0.0):
    """Outline of the chassis: the head-shell rectangle with its four corners cut off square to each hip."""
    bx, by, c = BODY_X - inset, BODY_Y - inset, (C_FACE - inset) / N45
    q = [(bx, c - bx), (c - by, by)]
    return q + [(-x, y) for x, y in reversed(q)] + [(-x, -y) for x, y in q] + [(x, -y) for x, y in reversed(q)]

def in_hip(sx, sy, solid, z=0.0):
    """Place a solid drawn in a hip frame (x out along the diagonal, y across, z up from the floor)."""
    return place(solid, T(sx * HIP_X, sy * HIP_Y, z) @ Rz(math.atan2(sy, sx)))

def hip_point(sx, sy, x, y):
    """A point given in a hip frame, in robot coordinates (x, y)."""
    a = math.atan2(sy, sx)
    return (sx * HIP_X + x * math.cos(a) - y * math.sin(a), sy * HIP_Y + x * math.sin(a) + y * math.cos(a))

def panel_cuts(inset=0.0, z0=-10.0, z1=300.0):
    """Tools: everything outside the two flat eye panels (moved in by 'inset')."""
    out = []
    for s in (1, -1):
        n, d, P = panel(s)
        F = frame(((d - inset) * n[0], (d - inset) * n[1], 0), (n[0], n[1], 0), (-n[1], n[0], 0))
        out.append(place(box(0, 200, -200, 200, z0, z1), F))
    return out

def _loop(z):
    return cq.selectors.BoxSelector((-400, -400, z - 0.05), (400, 400, z + 0.05))

def chassis_block(inset, h, ch, fr, r=TUB_R):
    """Rounded octagon, standing on z = 0, with a 45 degree edge round the bottom and a round above that."""
    b = cq.Workplane("XY").polyline(octagon(inset)).close().extrude(h).edges("|Z").fillet(r)
    b = b.faces("<Z").edges().chamfer(ch)
    return b.edges(_loop(ch)).fillet(fr)

def pebble(inset, h, ch, fr):
    """Head shape: rounded in plan; the top edge starts at 45 degrees (it prints roof down) and then rounds into the wall."""
    b = cq.Workplane("XY").rect(2 * (BODY_X - inset), 2 * (BODY_Y - inset)).extrude(h).edges("|Z").fillet(R_CORNER - inset)
    b = b.faces(">Z").edges().chamfer(ch)
    return b.edges(_loop(h - ch)).fillet(fr)

# deck layout (robot x, y) -------------------------------------------------------------
RADXA = (0.0, -42.0)             # Radxa Zero 3W, 65 x 30, holes 58 x 23 (M2.5). Long side across, pin rows toward the back, USB sockets toward the front
ADAPTER = (0.0, 39.5)            # Waveshare Bus Servo Adapter (A), 42 x 33, long side across. Holes 37 x 28 (M2)
REG_B = (52.0, -6.0)             # Hobbywing UBEC 3A (the 5 V converter): flat on the deck, long side front to back, its front end under the hub tray
IMU = (0.0, 6.5)                 # Adafruit LSM6DS3TR-C, 25.4 x 17.8, long side across, under the hub tray. Holes 20.3 x 12.7
PASS = (8.0, -16.0)              # slot that takes the switch's wires (5 and 7) down to the belly
HUB = (0.0, 6.5)                 # hub tray: middle of its bays
HUB_Z = Z_LIDBASE + 10.0         # underside of the hub tray: clears the motion sensor and the converter
HUB_TABS = [(35.6, -12.6), (-35.6, -12.6)]   # the hub tray's two screw tabs, toward the back
HUB_PADS = [(35.6, 17.0), (-35.6, 17.0)]     # and the two pads it rests on at the front
SHELF_Y = (22.0, 58.5)           # fuse shelf: back and front edge. It sits over the bus adapter
SHELF_X = 57.0                   # half width at the back edge; the front corners follow the eye panels
SHELF_Z = Z_LIDBASE + 20.5       # underside of the fuse shelf
SHELF_POSTS = [(26.5, 55.0), (-26.5, 55.0), (50.5, 25.5), (-50.5, 25.5)]
TIE_SLOTS = [(REG_B[0] + sx * 8.8, y) for sx in (1, -1) for y in (-22.0, -11.0)]   # two cable ties round the back half of the converter, behind the hub tray
LID_SCREW_Y = (-12.0, 12.0)
NUT25_AF, NUT25_T = 5.0, 2.0     # M2.5 nut for the head-shell screws
# eight more deck screws, beside the hips (v0.5): two per hip, either side of the turn motor's tail
HIP_POSTS = [hip_point(sx, sy, -18.0, s * 14.0) for sx, sy in LEGS for s in (1, -1)]
TUB_BOSS = [(BODY_X - WALL - 3.1, 0), (-(BODY_X - WALL - 3.1), 0), (20.0, 64.3), (-20.0, 64.3), (20.0, -64.3), (-20.0, -64.3)] + HIP_POSTS
# battery bay: takes a ready-made 2S pack up to 74 x 43 x 24 mm (ZOHD Lionpack 3500 mAh is 72 x 38 x 19.5)
DOOR_GAP = 0.5                   # the door is this much smaller than the opening, all round
TRAY = (21.5, 37.0, 10.4)        # cradle for the pack: half width, half length between its end lips, wall height
DOOR = (TRAY[0] + 2.0, 45.5)     # half width, half length of the door plate
BATT_OPEN = (DOOR[0] + DOOR_GAP, DOOR[1] + DOOR_GAP)   # half width, half length of the battery opening in the belly
BAR_Y = (TRAY[1] + 1.4 + 0.3, 48.7)   # two bars cross the opening inside the chassis, one at each end; the door screws into nuts in them
BAR_Z = (1.2, 7.8)               # bar: gap above the door plate (2.8 mm above the print bed), and its top, both measured from the belly floor.
                                 # Pads on the door fill the gap, so the door stops flush when its screws are tight
NUT_Z = 2.6                      # M3 nut slot in each bar, from the belly floor
NUT_AF, NUT_T = 5.5, 2.4         # M3 nut: across flats, thickness. NUT_AF is the width of every M3 nut slot (raise it by 0.2 if a nut will not go in)
M3_CLEAR = 1.7                   # M3 clearance radius
CSK3_R = 2.85                    # countersink for a flat-head M3 (5.6 head)
DOOR_SCREWS = [(12.0, 41.7), (-12.0, 41.7), (12.0, -41.7), (-12.0, -41.7)]   # M3 x 8 flat-head machine screws, from below, into M3 nuts
PACK_Z = Z_BELLY + WALL + 0.2    # underside of the pack, in the door's cradle
TIE_BRIDGES = [(sx * 31.0, sy * 12.0) for sx in (1, -1) for sy in (1, -1)]   # belly floor: the main fuse is tied at the left, the alarm at the right
SMILE = (0.0, 92.0, 10.0, 48.0, 1.6)   # centre x, centre z, radius, half angle, slot width

def tub():
    """Chassis. Rounded belly, four pads that seat the hip turn motors, 14 posts for the deck screws, open top. Prints belly down."""
    h = Z_DECK - Z_BELLY
    outer = cut(chassis_block(0, h, TUB_CH, TUB_FR), *panel_cuts(0)).translate((0, 0, Z_BELLY))
    inner = cut(chassis_block(WALL, h, TUB_CH - WALL + WALL * SQ, TUB_FR - WALL, r=TUB_R - WALL), *panel_cuts(WALL)).translate((0, 0, Z_BELLY + WALL))
    shell = outer.cut(inner)
    adds, tools = [], []
    for sx, sy in LEGS:
        for y0, y1 in ((4.4, MW / 2 + 0.6), (-MW / 2 - 0.6, -4.4)):                  # two rails, one under each screw
            adds.append(in_hip(sx, sy, box(-TAIL - 1.5, -SETBACK, y0, y1, Z_BELLY + 0.5, HIP_Z - FACE)))
        tools.append(in_hip(sx, sy, box(-SETBACK - WALL - 2, HEAD + 6, -MW / 2 - 0.3, MW / 2 + 0.3, HIP_Z - FACE, Z_DECK + 1)))   # slot for the motor case
        for y in (HOLE_X, -HOLE_X):
            tools.append(in_hip(sx, sy, cyl('z', -HOLE_TAIL, y, M2_CLEAR, Z_BELLY - 1, HIP_Z - FACE + 0.1)))
            tools.append(in_hip(sx, sy, cyl('z', -HOLE_TAIL, y, 2.3, Z_BELLY - 1, HIP_Z - FACE - 3.0)))                         # deep counterbore: 3 mm left under the motor, so an M2 x 6 goes 3.0 mm in
    for x, y in TUB_BOSS:
        adds.append(cyl('z', x, y, 3.5, Z_BELLY + 0.5, Z_DECK))
        tools.append(cyl('z', x, y, M25_PILOT, Z_DECK - 10, Z_DECK + 0.1))
    zf = Z_BELLY + WALL                                                             # belly floor, inside
    for s in (1, -1):                                                              # two bars across the battery opening: the door screws into nuts in them
        y0, y1 = sorted((s * BAR_Y[0], s * BAR_Y[1]))
        adds.append(box(-BATT_OPEN[0] - 4, BATT_OPEN[0] + 4, y0, y1, zf + BAR_Z[0], zf + BAR_Z[1]))
        for sx in (1, -1):
            x0, x1 = sorted((sx * (BATT_OPEN[0] + 0.2), sx * (BATT_OPEN[0] + 4)))
            adds.append(box(x0, x1, y0, y1, zf - 0.1, zf + BAR_Z[0] + 0.1))             # feet at the sides of the opening
        f0, f1 = sorted((s * (BATT_OPEN[1] + 0.2), s * BAR_Y[1]))
        adds.append(box(-BATT_OPEN[0] - 4, BATT_OPEN[0] + 4, f0, f1, zf - 0.1, zf + BAR_Z[0] + 0.1))   # foot beyond the end of the opening
    for x, y in DOOR_SCREWS:
        tools.append(cyl('z', x, y, M3_CLEAR, zf + BAR_Z[0] - 0.1, zf + BAR_Z[1] + 0.1))
        s = 1 if y > 0 else -1
        y0, y1 = sorted((s * (BAR_Y[0] - 0.1), y + s * (NUT_AF / math.sqrt(3) + 0.2)))
        tools.append(box(x - NUT_AF / 2, x + NUT_AF / 2, y0, y1, zf + NUT_Z, zf + NUT_Z + NUT_T + 0.2))   # nut slot, open to the battery opening
    for x, y in TIE_BRIDGES:                                                        # little bridges a cable tie passes under
        adds.append(box(x - 1.5, x + 1.5, y - 4.0, y + 4.0, zf - 0.1, zf + 3.0))
        tools.append(box(x - 1.6, x + 1.6, y - 2.2, y + 2.2, zf - 0.2, zf + 1.6))
    tools.append(box(-BATT_OPEN[0], BATT_OPEN[0], -BATT_OPEN[1], BATT_OPEN[1], Z_BELLY - 1, Z_BELLY + WALL + 1))             # battery opening
    return cut(union(shell, *adds).intersect(outer), *tools)

def deck():
    """Flat plate over the chassis. Clamps the four hip turn motors from above and carries the electronics. Prints flat."""
    z0, z1 = Z_DECK, Z_LIDBASE
    plate = cq.Workplane("XY").polyline(octagon()).close().extrude(z1 - z0).edges("|Z").fillet(TUB_R)
    plate = cut(plate, *panel_cuts(0)).translate((0, 0, z0))
    adds, tools = [], []
    for sx, sy in LEGS:
        tools.append(in_hip(sx, sy, box(PLUG_END, HEAD + 6, -MW / 2 - 4, MW / 2 + 4, z0 - 1, z1 + 1)))                       # keep clear of the idler horn, the fork and the two sockets on top of the motor
        for y in (HOLE_X, -HOLE_X):
            tools.append(in_hip(sx, sy, cyl('z', -HOLE_TAIL, y, M2_CLEAR, z0 - 1, z1 + 1)))                                 # M2 x 6 pan-head: 4.0 mm into the motor
    for x, y in TUB_BOSS:
        tools.append(cyl('z', x, y, M25_CLEAR, z0 - 1, z1 + 1))
    def post(x, y, r, h, pilot, r_top=None):
        if r_top is None:
            adds.append(cyl('z', x, y, r, z1 - 0.1, z1 + h))
        else:                                                                      # tall posts flare out at the foot
            adds.append(cq.Workplane("XY").add(cq.Solid.makeCone(r, r_top, h + 0.1, cq.Vector(x, y, z1 - 0.1), cq.Vector(0, 0, 1))))
        if pilot:                                                                  # short posts: the pilot goes on through the deck, so the screw never meets solid plastic
            tools.append(cyl('z', x, y, pilot, z1 - 2.5 if h < 9.0 else z1 + h - 9.0, z1 + h + 0.1))
    for sx in (29.0, -29.0):                                                       # brain: M2.5 x 6
        for sy in (11.5, -11.5):
            post(RADXA[0] + sx, RADXA[1] + sy, 3.0, 4.0, M25_PILOT)
    for sx in (18.5, -18.5):                                                       # bus adapter: M2 x 6
        for sy in (14.0, -14.0):
            post(ADAPTER[0] + sx, ADAPTER[1] + sy, 2.4, 3.0, M2_PILOT)
    for k, (sx, sy) in enumerate(((1, 1), (-1, -1), (1, -1), (-1, 1))):            # motion sensor: four posts, M2 x 6 into two opposite corners
        post(IMU[0] + sx * 10.16, IMU[1] + sy * 6.35, 1.8, 2.5, M2_PILOT if k < 2 else None)
    for x, y in HUB_TABS:                                                           # hub tray: two posts (M2.5 x 6) and two pads
        post(x, y, 3.0, HUB_Z - z1, M25_PILOT)
    for x, y in HUB_PADS:
        post(x, y, 3.0, HUB_Z - z1, None)
    for x, y in SHELF_POSTS:                                                        # fuse shelf: four tall posts (M2.5 x 8)
        post(x, y, 5.0, SHELF_Z - z1, M25_PILOT, r_top=3.2)
    for x, y in TIE_SLOTS:
        tools.append(box(x - 0.8, x + 0.8, y - 2.0, y + 2.0, z0 - 1, z1 + 1))
    tools.append(box(PASS[0] - 9, PASS[0] + 9, PASS[1] - 5, PASS[1] + 5, z0 - 1, z1 + 1))
    # camera rails at the front: the board slides down into their grooves, lens forward
    yi = BODY_Y - LW                                                              # inner face of the head shell's front wall
    for s in (1, -1):
        x0, x1 = sorted((s * 11.3, s * 14.3))
        adds.append(box(x0, x1, yi - 8.0, yi - 0.6, z1 - 0.1, CAM_Z + 16.0))
        g0, g1 = sorted((s * 11.2, s * 12.8))
        tools.append(box(g0, g1, yi - 6.95, yi - 5.45, CAM_Z - 9.5, CAM_Z + 16.1))                                # groove for the 25 mm wide, 1.0 mm thick board: 0.25 each side
        f0, f1 = sorted((s * 11.3, s * 16.5))                                                                     # stops short of the deck screw heads at x = +-20
        adds.append(cq.Workplane("XZ").polyline([(f0, z1 - 0.1), (f1, z1 - 0.1), (f0, z1 + 7.0)]).close().extrude(-5.0).translate((0, yi - 6.4, 0)) if s > 0
                    else cq.Workplane("XZ").polyline([(f1, z1 - 0.1), (f0, z1 - 0.1), (f1, z1 + 7.0)]).close().extrude(-5.0).translate((0, yi - 6.4, 0)))   # gusset on the outside of each rail
    for s in (1, -1):                                                              # blocks the head shell screws into: an M2.5 nut drops into each from the top
        for y in LID_SCREW_Y:
            xo = s * (BODY_X - LW - 0.3)
            x0, x1 = sorted((xo, xo - s * 8.0))
            adds.append(box(x0, x1, y - 4, y + 4, z1 - 0.1, z1 + 9))
            tools.append(cyl('x', y, z1 + 4.5, M25_CLEAR, x0 - 0.1, x1 + 0.1))
            xn = xo - s * 3.5
            tools.append(box(xn - NUT25_T / 2 - 0.15, xn + NUT25_T / 2 + 0.15, y - NUT25_AF / math.sqrt(3) - 0.2, y + NUT25_AF / math.sqrt(3) + 0.2,
                             z1 + 4.5 - NUT25_AF / 2 - 0.1, z1 + 9.1))
    return cut(union(plate, *adds), *tools)

# hub tray: eight lever connectors (Wago 221) stand in three bays, wire holes up ------------------
WAGO = {2: (13.1, 8.1, 18.7), 3: (18.6, 8.1, 18.7), 5: (29.8, 8.1, 18.7)}   # width, thickness, depth (Wago 221-412/413/415)
HUB_BAY = (31.0, 25.0)           # inside of one bay: across, front to back (three 5-way side by side)
HUB_T, HUB_FLOOR, HUB_H = 1.2, 1.6, 14.0
HUB_STUB = 4.0                   # the walls between bays are stubs this long at the front and back: they keep each bay's connectors apart

def hub_tray():
    """Three bays side by side: data (left), ground (middle), plus (right); two screw tabs at the back.
    A window under each bay saves plastic. Prints flat plate down, walls up."""
    bx, by = HUB_BAY
    n = 3
    L = n * bx + (n + 1) * HUB_T
    yc = HUB[1]
    y0, y1 = yc - by / 2 - HUB_T, yc + by / 2 + HUB_T
    p = [box(-L / 2, L / 2, y0, y1, HUB_Z, HUB_Z + HUB_H)]
    tools = [box(-L / 2 + HUB_T, L / 2 - HUB_T, yc - by / 2, yc + by / 2, HUB_Z + HUB_FLOOR, HUB_Z + HUB_H + 0.1)]
    for k in range(1, n):                                                          # stubs between the bays
        x = -L / 2 + HUB_T / 2 + k * (bx + HUB_T)
        for ya, yb in ((yc - by / 2 - 0.1, yc - by / 2 + HUB_STUB), (yc + by / 2 - HUB_STUB, yc + by / 2 + 0.1)):
            p.append(box(x - HUB_T / 2, x + HUB_T / 2, ya, yb, HUB_Z + HUB_FLOOR - 0.1, HUB_Z + HUB_H))
    for k in range(n):                                                             # a window under each bay
        xm = -L / 2 + HUB_T + k * (bx + HUB_T) + bx / 2
        tools.append(box(xm - 10.0, xm + 10.0, yc - 6.0, yc + 6.0, HUB_Z - 0.1, HUB_Z + HUB_FLOOR + 0.1))
    for x, y in HUB_TABS:
        p.append(box(x - 5, x + 5, y - 4, y0 + 0.1, HUB_Z, HUB_Z + HUB_FLOOR))
        tools.append(cyl('z', x, y, M25_CLEAR, HUB_Z - 0.1, HUB_Z + HUB_FLOOR + 0.1))
    body = cut(p[0], *tools[:1])
    return cut(union(body, *p[1:]), *tools[1:])

def shelf_outline():
    """Plan of the fuse shelf: back edge across the deck, front corners cut along the eye panels (2 mm inside the head shell)."""
    n, d, _P = panel(1)
    dn = d - LW - 2.0
    xf = (dn - n[1] * SHELF_Y[1]) / n[0]                                           # front corner, on the panel line
    ys = (dn - n[0] * SHELF_X) / n[1]                                              # where the panel line meets the side
    return [(-SHELF_X, SHELF_Y[0]), (SHELF_X, SHELF_Y[0]), (SHELF_X, ys), (xf, SHELF_Y[1]), (-xf, SHELF_Y[1]), (-SHELF_X, ys)]

def shelf():
    """Fuse shelf on four tall posts over the bus adapter: the five chain fuses tied on the right half, the USB hub on the left.
    Prints flat plate down, rim up."""
    pts = shelf_outline()
    z0 = SHELF_Z
    plate = cq.Workplane("XY").polyline(pts).close().extrude(2.0).translate((0, 0, z0))
    inner = cq.Workplane("XY").polyline(pts).close().offset2D(-1.6).extrude(3.1).translate((0, 0, z0 + 2.0))
    rim = cq.Workplane("XY").polyline(pts).close().extrude(3.0).translate((0, 0, z0 + 2.0)).cut(inner)
    tools = [cyl('z', x, y, M25_CLEAR, z0 - 0.1, z0 + 5.1) for x, y in SHELF_POSTS]
    tools += [cyl('z', x, y, 3.0, z0 + 2.0, z0 + 5.1) for x, y in SHELF_POSTS]    # the rim stops round each screw, so its head seats on the plate
    for x in (-40.0, -16.0, 10.0, 46.0):                                           # pairs of slots for cable ties
        for y in (28.0, 48.0):
            tools.append(box(x - 2.0, x + 2.0, y - 0.8, y + 0.8, z0 - 0.1, z0 + 2.1))
    for x in (-4.0, 4.0):                                                          # gaps in the back rim for the leads
        tools.append(box(x - 3.0, x + 3.0, SHELF_Y[0] - 0.1, SHELF_Y[0] + 1.7, z0 + 2.0, z0 + 5.1))
    return cut(union(plate, rim), *tools)

def lid():
    """Head shell: a pebble with two flat eye panels, the roof that carries the shoulder, and arches over the four hips.
    Prints roof down, no supports."""
    h = Z_TOP - Z_LIDBASE
    outer = cut(pebble(0, h, TOP_CH, TOP_R), *panel_cuts(0)).translate((0, 0, Z_LIDBASE))
    inner = cut(pebble(LW, h - ROOF, TOP_CH - ROOF + LW * SQ, TOP_R - LW), *panel_cuts(LW)).translate((0, 0, Z_LIDBASE))
    shell = outer.cut(inner)
    adds, tools = [], []
    for sx, sy in LEGS:                                                            # arch over each hip
        tools.append(place(box(C_FACE, 160, -90, 90, Z_LIDBASE - 1, Z_NOTCH), Rz(math.atan2(sy, sx))))
    yf, yb = BODY_Y, -BODY_Y
    # face: a shallow seat for each eye, and the camera hole (the camera itself stands in rails on the deck)
    for s in (1, -1):
        tools.append(place(cyl('z', 0, 0, 20.7, -0.4, 2.0), panel_frame(s, EYE_Z)))
    tools.append(cyl('y', 0, CAM_Z, 3.75, yf - LW - 1, yf + 1))
    def ease(x0, x1, ywall, depth, zend, inward):
        """Cut the roof-side end of a rail at 45 degrees so it prints without support (the shell prints roof down)."""
        yin = ywall + inward * (depth + 0.1)
        tri = cq.Workplane("YZ").polyline([(yin, zend + 0.1), (yin, zend - depth - 0.1), (ywall, zend + 0.1)]).close().extrude(x1 - x0 + 0.2).translate((x0 - 0.1, 0, 0))
        tools.append(tri)
    for s in (1, -1):
        ease(*sorted((s * 15.3, s * 17.8)), yb + LW, 9.0, 112.0, 1)
    # the switch sits where the back wall starts to curve: a boss inside and a flat facet outside give its nut a square seat
    sx, sz, _sr = SWITCH
    adds.append(box(sx - 10.5, sx + 10.5, yb, SWITCH_PANEL_Y, sz - 12.0, sz + 14.0))
    ease(sx - 10.5, sx + 10.5, yb + LW, SWITCH_PANEL_Y - (yb + LW), sz + 14.0, 1)
    cx, cy = BODY_X - R_CORNER, BODY_Y - R_CORNER
    xe = abs(sx) + SWITCH_SEAT
    y_face = -(cy + math.sqrt(R_CORNER ** 2 - (xe - cx) ** 2)) if xe > cx else yb
    tools.append(cyl('y', sx, sz, SWITCH_SEAT, yb - 5, y_face))
    # roof: shoulder mount bosses, cable hole, sound holes over the two microphones
    zr = Z_TOP - ROOF
    for x, y in SH_MOUNT:
        adds.append(cyl('z', x, SH_Y + y, 3.4, zr - 6.0, zr + 0.1))
        tools.append(cyl('z', x, SH_Y + y, M25_PILOT, zr - 6.1, Z_TOP + 1))
    for s in (1, -1):
        for dx, dy in ((0, 0), (3, 0), (-3, 0), (0, 3), (0, -3)):
            tools.append(cyl('z', s * MIC[0] + dx, MIC[1] + dy, 0.8, zr - 1, Z_TOP + 1))
    tools.append(cyl('z', 0, SH_Y - 37.0, 4.5, zr - 1, Z_TOP + 1))
    for s in (1, -1):                                                              # ribs under the roof, from the shoulder screws toward the face
        adds.append(box(s * 18.0 - 1.0, s * 18.0 + 1.0, SH_Y - 52.0, BODY_Y - 15.5, zr - 6.0, zr + 0.1))
    adds.append(box(-19.0, 19.0, SH_Y - 28.0, SH_Y - 26.0, zr - 6.0, zr + 0.1))
    # back wall: speaker rails and grille, the switch's round hole
    yi = yb + LW
    for s in (1, -1):
        x0, x1 = sorted((s * 15.3, s * 17.8))
        adds.append(box(x0, x1, yi - 0.6, yi + 9.0, Z_LIDBASE + 8, 112.0))
        g0, g1 = sorted((s * 14.0, s * 16.2))
        tools.append(box(g0, g1, yi + 1.0, yi + 7.6, Z_LIDBASE + 7, 111.0))
    for i in range(-2, 3):
        for j in range(-2, 3):
            if abs(i) + abs(j) <= 3:
                tools.append(cyl('y', i * 4.2, SPK_Z + j * 4.2, 1.1, yb - 1, yb + LW + 1))
    tools.append(cyl('y', SWITCH[0], SWITCH[1], SWITCH[2], yb - 3, SWITCH_PANEL_Y + 1))   # toggle switch: its threaded neck comes through from inside
    # sides: screws into the nuts in the deck, vents
    for s in (1, -1):
        for y in LID_SCREW_Y:
            tools.append(cyl('x', y, Z_LIDBASE + 4.5, M25_CLEAR, BODY_X - LW - 1, BODY_X + 1) if s > 0 else cyl('x', y, Z_LIDBASE + 4.5, M25_CLEAR, -BODY_X - 1, -BODY_X + LW + 1))
        for k in range(4):
            y = -20.0 + k * 7.0
            tools.append(box(BODY_X - LW - 1, BODY_X + 1, y - 1.0, y + 1.0, 96.0, 110.0) if s > 0 else box(-BODY_X - 1, -BODY_X + LW + 1, y - 1.0, y + 1.0, 96.0, 110.0))
    return cut(union(shell, *adds).intersect(outer), *tools)

SPK_Z = 97.0                     # speaker centre height on the back wall
MIC = (29.0, -22.0)              # the two groups of five sound holes in the roof (x is +-); the sound card is taped under the left one
SWITCH = (-30.0, 104.0, 6.1)     # toggle switch (Cole Hersee 5582): x, height, radius of its hole. The switch's neck is 15/32 in (11.9 mm)
SWITCH_SEAT = 9.0                # radius of the flat facet its nut and lock washer seat on
SWITCH_PANEL_Y = -63.0           # inner face of the boss the switch body presses against: the panel is about 4.4 mm thick (the switch takes up to 6.35)
BLUSH = (4.4, 2.2)               # cheek: half width, half height
BLUSH_Z, BLUSH_S = 82.5, -17.0   # height, and how far it sits toward the nose from the middle of the eye panel

def eye(r=EYE_R, sink=EYE_SINK, lip=0.4):
    """Glossy black dome. Flat back sits in the seat on the head shell. Local frame: dome along +z. Prints flat side down."""
    rb = math.sqrt(r * r - sink * sink)
    m = (math.atan2(sink, rb) + math.pi / 2) / 2
    prof = (cq.Workplane("XY").moveTo(0, -lip).lineTo(rb, -lip).lineTo(rb, 0)
            .threePointArc((r * math.cos(m), -sink + r * math.sin(m)), (0, r - sink)).close())
    return prof.revolve(360, (0, 0, 0), (0, 1, 0)).rotate((0, 0, 0), (1, 0, 0), 90)

def battery_door():
    """Belly door and cradle for a ready-made 2S pack. It goes in from below and four flat-head M3 screws hold it to nuts in
    the two bars in the chassis. Prints plate down, no supports."""
    z0, zf = Z_BELLY, Z_BELLY + WALL
    hx, hy = DOOR
    p = [cq.Workplane("XY").rect(2 * hx, 2 * hy).extrude(WALL).edges("|Z").fillet(1.5).translate((0, 0, z0))]
    w, l, h = TRAY
    for s in (1, -1):
        x0, x1 = sorted((s * w, s * (w + 1.6)))
        p.append(box(x0, x1, -l - 1.4, l + 1.4, zf - 0.1, zf + h))                    # side walls
        y0, y1 = sorted((s * l, s * (l + 1.4)))
        p.append(box(-w - 1.6, w + 1.6, y0, y1, zf - 0.1, zf + h))                    # end lips, just inside the chassis bars
    for x, y in DOOR_SCREWS:                                                          # pads under the bars: the door stops flush, and the countersinks have plastic under them
        p.append(cyl('z', x, y, 3.6, zf - 0.1, zf + BAR_Z[0]))
    tools = []
    for x, y in DOOR_SCREWS:
        tools += [cyl('z', x, y, M3_CLEAR, z0 - 0.1, zf + 0.1), cone('z', x, y, CSK3_R, M3_CLEAR, z0 - 0.01, z0 + CSK3_R - M3_CLEAR)]
    for s in (1, -1):                                                                 # slots for a cable tie round the pack
        x0, x1 = sorted((s * (w - 2.6), s * (w - 0.4)))
        tools.append(box(x0, x1, -6, 6, z0 - 0.1, zf + 0.1))
    tools.append(box(-6, 6, l - 0.1, l + 1.5, zf + 2.5, zf + h + 0.1))                 # gap in one end lip for the pack's leads
    return cut(union(*p), *tools)

# ------------------------------------------------------------------ test piece (print this first)
TP_L, TP_W, TP_T = 75.0, 39.0, 2.0   # base plate: length, width, thickness

def test_piece():
    """Checks the fits that decide whether the rest will work, with one motor, before anything else is printed:
    a motor pocket (CHK_IN and its countersunk M2 holes), a fork (ARM_IN and the raised screw seats), an M2 and an M2.5
    pilot hole, and an M3 nut in its slot with a flat-head screw from below (the battery door's fixing). Prints flat base down.
    Frame: base plate on z = 0, from x = 0 to TP_L and y = 0 to TP_W."""
    yc = TP_W / 2
    p = [box(0, TP_L, 0, TP_W, 0, TP_T)]
    tools = []
    # screw block (back) and nut block (front), at the left end
    p.append(box(3, 14, 25, 36, TP_T - 0.1, TP_T + 11))
    tools += [cyl('z', 6.5, 30.5, M2_PILOT, TP_T + 2, TP_T + 11.1), cyl('z', 10.5, 30.5, M25_PILOT, TP_T + 2, TP_T + 11.1)]
    p.append(box(3, 14, 3, 14, TP_T - 0.1, TP_T + 9))
    tools += [cyl('z', 8.5, 8.5, M3_CLEAR, -0.1, TP_T + 9.1),
              cone('z', 8.5, 8.5, CSK3_R, M3_CLEAR, -0.01, CSK3_R - M3_CLEAR),
              box(2.9, 8.5 + NUT_AF / math.sqrt(3) + 0.2, 8.5 - NUT_AF / 2, 8.5 + NUT_AF / 2, TP_T + 3.0, TP_T + 3.0 + NUT_T + 0.2)]   # nut slot, open to the left
    # fork gauge: two arms as on every fork, shaft across the plate (y) at height za. The motor's case points up or to the right
    xa, za = 30.0, TP_T + 14.5
    arms = []
    for s in (1, -1):
        y0, y1 = sorted((s * ARM_IN, s * ARM_OUT))
        arms += [cyl('y', xa, za, DISC_R, y0, y1), box(xa - DISC_R, xa + DISC_R, y0, y1, TP_T - 0.1, za)]
    p.append(cut(union(*arms, *arm_domes('y', xa, za)), *arm_holes('y', xa, za)).translate((0, yc, 0)))
    # pocket gauge: the two walls of a motor pocket. As in every pocket they hold the motor's tail end only, and stop short of
    # its horns and sockets (14.4 mm from the shaft). The motor lies on the plate, tail first between the walls, tail end at xt.
    xt = 47.0
    for s in (1, -1):
        y0, y1 = sorted((yc + s * CHK_IN, yc + s * CHK_OUT))
        p.append(box(xt - 1.0, xt + TAIL + PLUG_END, y0, y1, TP_T - 0.1, TP_T + CLR + MW + 2.0))
        for z in (-HOLE_X, HOLE_X):
            tools += [t.translate((0, yc, 0)) for t in cheek_hole('y', xt + TAIL - HOLE_TAIL, TP_T + CLR + MW / 2 + z, s * CHK_OUT, s)]
    return cut(union(*p), *tools)
