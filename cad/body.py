"""Body of the scorpion spider v0.4: rounded chassis, battery door, deck, pebble head shell, eyes. Robot frame, millimetres."""
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
RADXA = (0.0, -22.0)             # Radxa Zero 3W with the ReSpeaker HAT on top, long side across the body
ADAPTER = (-30.0, 23.5)          # Waveshare Bus Servo Adapter (A), 42 x 33, long side across the body. Holes 37 x 28
REG_B = (30.0, 40.0)             # Pololu D24V25F5, 17.8 x 17.8
IMU = (16.0, 16.0)               # Adafruit LSM6DS3TR-C, 25.4 x 17.8
PASS = (0.0, 1.0)                # cable pass-through: battery and charger wires come up here
LID_SCREW_Y = (-12.0, 12.0)
TUB_BOSS = [(BODY_X - WALL - 3.1, 0), (-(BODY_X - WALL - 3.1), 0), (20.0, 64.3), (-20.0, 64.3), (20.0, -64.3), (-20.0, -64.3)]
BATT_OPEN = (21.0, 42.0)         # half width, half length of the battery opening in the belly
DOOR_GAP = 0.25                  # the door is this much smaller than the opening, all round
BAR_Y = (36.0, 44.0)             # two bars cross the opening inside the chassis, one at each end; the door screws into them
BAR_Z = (0.6, 4.6)               # bar: gap above the door plate, and its top, both measured from the belly floor
DOOR_SCREWS = [(12.0, 39.0), (-12.0, 39.0), (12.0, -39.0), (-12.0, -39.0)]   # M2 x 8 flat-head tapping, from below
TRAY = (19.0, 34.2, 8.0)         # cradle for the 2S pack: half width, half length between its end lips, wall height
PACK_Z = Z_BELLY + WALL + 0.2    # underside of the two cells
CHG_SIZE = (18.0, 25.0)          # 2S USB-C charge board: width, length (a typical board, check yours)
CHG_Z = 57.0                     # underside of the charge board
USBC = (4.9, 2.0)                # half width and half height of the opening for the USB-C socket
SMILE = (0.0, 92.0, 10.0, 48.0, 1.6)   # centre x, centre z, radius, half angle, slot width

def tub():
    """Chassis. Rounded belly, four pads that seat the hip turn motors, open top. Prints belly down."""
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
            tools.append(in_hip(sx, sy, cyl('z', -HOLE_TAIL, y, 2.3, Z_BELLY - 1, HIP_Z - FACE - 3.0)))                         # deep counterbore: 3 mm left under the motor
    for x, y in TUB_BOSS:
        adds.append(cyl('z', x, y, 3.5, Z_BELLY + 0.5, Z_DECK))
        tools.append(cyl('z', x, y, M25_PILOT, Z_DECK - 10, Z_DECK + 0.1))
    zf = Z_BELLY + WALL                                                             # belly floor, inside
    for s in (1, -1):                                                              # two bars across the battery opening: the door screws into them
        y0, y1 = sorted((s * BAR_Y[0], s * BAR_Y[1]))
        adds.append(box(-BATT_OPEN[0] - 4, BATT_OPEN[0] + 4, y0, y1, zf + BAR_Z[0], zf + BAR_Z[1]))
        for sx in (1, -1):
            x0, x1 = sorted((sx * (BATT_OPEN[0] + 0.2), sx * (BATT_OPEN[0] + 4)))
            adds.append(box(x0, x1, y0, y1, zf - 0.1, zf + BAR_Z[0] + 0.1))             # feet at the sides of the opening
        f0, f1 = sorted((s * (BATT_OPEN[1] + 0.2), s * BAR_Y[1]))
        adds.append(box(-BATT_OPEN[0] - 4, BATT_OPEN[0] + 4, f0, f1, zf - 0.1, zf + BAR_Z[0] + 0.1))   # foot beyond the end of the opening
    for x, y in DOOR_SCREWS:
        tools.append(cyl('z', x, y, 0.85, zf + BAR_Z[0] - 0.1, zf + BAR_Z[1] + 0.1))
    yw = -BODY_Y + WALL                                                             # charge board: a shelf on two walls, against the back wall
    hw, ln = CHG_SIZE[0] / 2 + 0.15, CHG_SIZE[1] + 0.6
    for s in (1, -1):
        x0, x1 = sorted((s * hw, s * (hw + 1.6)))
        adds.append(box(x0, x1, yw - 0.1, yw + ln + 1.6, Z_BELLY + 0.5, CHG_Z + 3.0))
    adds.append(box(-hw - 1.6, hw + 1.6, yw + ln, yw + ln + 1.6, CHG_Z - 8.0, CHG_Z + 3.0))                                     # end wall: takes the push when a cable is plugged in. Open underneath, so nothing is sealed in
    adds.append(box(-hw - 1.6, hw + 1.6, yw - 0.1, yw + ln + 1.6, CHG_Z - 1.6, CHG_Z))                                          # shelf, bridges between the two walls
    tools.append(box(-USBC[0], USBC[0], -BODY_Y - 1, yw + 0.5, CHG_Z + 3.25 - USBC[1], CHG_Z + 3.25 + USBC[1]))                # opening for the USB-C socket
    tools.append(box(-3.0, 3.0, yw + ln - 0.1, yw + ln + 1.7, CHG_Z + 0.2, CHG_Z + 3.1))                                        # gap in the end wall for the board's wires
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
            tools.append(in_hip(sx, sy, cyl('z', -HOLE_TAIL, y, M2_CLEAR, z0 - 1, z1 + 1)))
    for x, y in TUB_BOSS:
        tools.append(cyl('z', x, y, M25_CLEAR, z0 - 1, z1 + 1))
    def post(x, y, r, h, pilot):
        adds.append(cyl('z', x, y, r, z1 - 0.1, z1 + h)); tools.append(cyl('z', x, y, pilot, z1 - 2.5, z1 + h + 0.1))
    for sx in (29.0, -29.0):                                                       # Radxa Zero 3W: 58 x 23 hole pattern, M2.5
        for sy in (11.5, -11.5):
            post(RADXA[0] + sx, RADXA[1] + sy, 3.0, 6.0, M25_PILOT)
    for sx in (18.5, -18.5):                                                       # bus adapter: 37 x 28 hole pattern, 2.5 mm holes, M2 tapping screws
        for sy in (14.0, -14.0):
            post(ADAPTER[0] + sx, ADAPTER[1] + sy, 2.4, 3.0, 0.85)
    def tray(c, w, l, h=3.0, t=1.6):                                              # shallow walled pocket for a small board
        x, y = c
        adds.append(box(x - w / 2 - t, x + w / 2 + t, y - l / 2 - t, y + l / 2 + t, z1 - 0.1, z1 + h))
        tools.append(box(x - w / 2, x + w / 2, y - l / 2, y + l / 2, z1, z1 + h + 0.1))
        tools.append(box(x - w / 2 + 3, x + w / 2 - 3, y - l / 2 - t - 0.1, y + l / 2 + t + 0.1, z1 + 1.0, z1 + h + 0.1))   # gaps for wires and a fingernail
    tray(REG_B, 18.3, 18.3)
    tray(IMU, 25.9, 18.3, h=2.5)
    tools.append(box(PASS[0] - 9, PASS[0] + 9, PASS[1] - 5, PASS[1] + 5, z0 - 1, z1 + 1))
    for s in (1, -1):                                                              # blocks the head shell screws into, from each side
        for y in LID_SCREW_Y:
            x0, x1 = sorted((s * (BODY_X - LW - 0.3), s * (BODY_X - LW - 8.3)))
            adds.append(box(x0, x1, y - 4, y + 4, z1 - 0.1, z1 + 9))
            tools.append(cyl('x', y, z1 + 4.5, M25_PILOT, x0 - 0.1 if s < 0 else x1 - 7.5, x0 + 7.5 if s < 0 else x1 + 0.1))
    return cut(union(plate, *adds), *tools)

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
    # face: a shallow seat for each eye ring, the camera hole and its slide-in rails
    for s in (1, -1):
        tools.append(place(cyl('z', 0, 0, 20.7, -0.4, 2.0), panel_frame(s, EYE_Z)))
    tools.append(cyl('y', 0, CAM_Z, 3.75, yf - LW - 1, yf + 1))
    yi = yf - LW                                                                  # inner face of the front wall
    for s in (1, -1):
        x0, x1 = sorted((s * 11.3, s * 14.3))
        adds.append(box(x0, x1, yi - 8.0, yi + 0.6, Z_LIDBASE, CAM_Z + 16.0))                                    # camera rails
        g0, g1 = sorted((s * 11.2, s * 12.8))
        tools.append(box(g0, g1, yi - 6.9, yi - 5.5, Z_LIDBASE - 1, CAM_Z + 15.0))                               # groove for the 25 x 24 mm board
    def ease(x0, x1, ywall, depth, zend, inward):
        """Cut the roof-side end of a rail at 45 degrees so it prints without support (the shell prints roof down)."""
        yin = ywall + inward * (depth + 0.1)
        tri = cq.Workplane("YZ").polyline([(yin, zend + 0.1), (yin, zend - depth - 0.1), (ywall, zend + 0.1)]).close().extrude(x1 - x0 + 0.2).translate((x0 - 0.1, 0, 0))
        tools.append(tri)
    for s in (1, -1):
        ease(*sorted((s * 11.3, s * 14.3)), yi, 8.0, CAM_Z + 16.0, -1)
        ease(*sorted((s * 15.3, s * 17.8)), yb + LW, 9.0, 112.0, 1)
    # roof: shoulder mount bosses, cable hole, sound holes over the two microphones
    zr = Z_TOP - ROOF
    for x, y in SH_MOUNT:
        adds.append(cyl('z', x, SH_Y + y, 3.4, zr - 6.0, zr + 0.1))
        tools.append(cyl('z', x, SH_Y + y, M25_PILOT, zr - 6.1, Z_TOP + 1))
    for s in (1, -1):
        for dx, dy in ((0, 0), (3, 0), (-3, 0), (0, 3), (0, -3)):
            tools.append(cyl('z', s * 29.0 + dx, RADXA[1] + dy, 0.8, zr - 1, Z_TOP + 1))
    tools.append(cyl('z', 0, SH_Y - 37.0, 4.5, zr - 1, Z_TOP + 1))
    for s in (1, -1):                                                              # ribs under the roof, from the shoulder screws toward the face
        adds.append(box(s * 18.0 - 1.0, s * 18.0 + 1.0, SH_Y - 52.0, BODY_Y - 15.5, zr - 6.0, zr + 0.1))
    adds.append(box(-19.0, 19.0, SH_Y - 28.0, SH_Y - 26.0, zr - 6.0, zr + 0.1))
    # back wall: speaker rails and grille, switch opening
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
    tools.append(box(SWITCH[0], SWITCH[1], yb - 1, yb + LW + 1, SWITCH[2], SWITCH[3]))                          # rocker switch, 8.8 x 13.5, upright
    # sides: screws into the deck, vents
    for s in (1, -1):
        for y in LID_SCREW_Y:
            tools.append(cyl('x', y, Z_LIDBASE + 4.5, M25_CLEAR, BODY_X - LW - 1, BODY_X + 1) if s > 0 else cyl('x', y, Z_LIDBASE + 4.5, M25_CLEAR, -BODY_X - 1, -BODY_X + LW + 1))
        for k in range(4):
            y = -20.0 + k * 7.0
            tools.append(box(BODY_X - LW - 1, BODY_X + 1, y - 1.0, y + 1.0, 96.0, 110.0) if s > 0 else box(-BODY_X - 1, -BODY_X + LW + 1, y - 1.0, y + 1.0, 96.0, 110.0))
    return cut(union(shell, *adds).intersect(outer), *tools)

SPK_Z = 97.0                     # speaker centre height on the back wall
SWITCH = (-27.3, -18.5, 90.0, 103.5)
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
    """Belly door and cradle for the 2S pack (two 18650 cells side by side with their protection board).
    It goes in from below and four flat-head screws hold it to the two bars in the chassis. Prints plate down, no supports."""
    z0, zf = Z_BELLY, Z_BELLY + WALL
    hx, hy = BATT_OPEN[0] - DOOR_GAP, BATT_OPEN[1] - DOOR_GAP
    p = [cq.Workplane("XY").rect(2 * hx, 2 * hy).extrude(WALL).edges("|Z").fillet(1.5).translate((0, 0, z0))]
    w, l, h = TRAY
    for s in (1, -1):
        x0, x1 = sorted((s * w, s * (w + 1.6)))
        p.append(box(x0, x1, -l - 1.4, l + 1.4, zf - 0.1, zf + h))                    # side walls
        y0, y1 = sorted((s * l, s * (l + 1.4)))
        p.append(box(-w - 1.6, w + 1.6, y0, y1, zf - 0.1, zf + h))                    # end lips, just inside the chassis bars
    tools = []
    for x, y in DOOR_SCREWS:
        tools += [cyl('z', x, y, M2_CLEAR, z0 - 0.1, zf + 0.1), cone('z', x, y, CSK_R, M2_CLEAR, z0 - 0.01, z0 + CSK_H)]
    for s in (1, -1):                                                                 # slots for a strap round the pack
        x0, x1 = sorted((s * (w - 2.6), s * (w - 0.4)))
        tools.append(box(x0, x1, -6, 6, z0 - 0.1, zf + 0.1))
    tools.append(box(-6, 6, l - 0.1, l + 1.5, zf + 2.5, zf + h + 0.1))                 # gap in one end lip for the pack's wires
    return cut(union(*p), *tools)
