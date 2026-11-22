"""Scorpion spider v0.5 (pillow, Feetech motors): printable parts, built around real components. Millimetres.

Robot frame: X = right, Y = forward, Z = up, origin on the floor under the middle of the body (standing).
Every part function returns a solid in that part's own frame; assembly.py places them.

v0.5 is v0.4 with the fixes from the v0.5 build pack (build-pack/, "Findings"): every sliding fit 0.25 mm or more,
pocket walls 2.35 mm, fork screw seats 0.6 mm higher, flat-head screws sunk flush under the shoulder motor,
a tighter foot socket, and a test piece to check the fits before anything else is printed.
"""
import math
from prim import *

# ------------------------------------------------------------------ real parts
# Feetech HD-1910-C001. Every number here is measured from Feetech's own STEP model (HD-1910-C001-20260902.stp).
# Case 20 x 34 x 23 mm. A 16 mm horn stands 3 mm proud of each face: the driven horn on one, the idler horn on the other (29 mm over both).
# Motor frame: origin on the shaft axis at mid-depth, Z = shaft (driven horn at +Z, idler at -Z), +Y = short "head" end, -Y = long "tail" end.
MW, MD = 20.0, 23.0              # case width (X), case depth (Z)
HEAD, TAIL = 9.5, 24.5           # shaft axis to head end / tail end (9.5 + 24.5 = 34)
HORN_R, HORN_T = 8.0, 3.0        # both horns; each has a 5 mm screw head in the middle, 0.8 mm (driven) or 0.4 mm (idler) proud
HOLE_X, HOLE_HEAD, HOLE_TAIL = 8.0, 7.5, 22.5   # four 1.6 mm holes per face for M2 tapping screws: +-8 across, 2 mm in from each end (3.5 mm deep on the horn face, 4.5 on the idler face)
PCD_R = 6.0                      # each horn: eight 1.6 mm holes on a 12 mm circle. The forks use four of them
FACE = MD / 2                    # 11.5: case face to mid-depth
# The two 3-pin bus sockets sit in notches on the IDLER face, one on each long side, just tail-ward of the horn. Plugs go in along the shaft.
PLUG_X0, PLUG_X1 = 4.7, 10.0     # each notch, across the case (mirrored on the other side); it is open to the side of the case
PLUG_Y0, PLUG_Y1 = -13.75, -3.8  # each notch, along the case
PLUG_DEEP = 10.0                 # how far the notch goes in from the idler face; the socket mouth is 2.55 mm inside the face
WIRE_W = 6.0                     # width of the wire channels cut in the idler-side cheeks
PLUG_END = PLUG_Y0 - 0.65        # -14.4: an idler-side cheek must stop here, so both sockets stay open

# ------------------------------------------------------------------ printed-joint standards
# A printer is accurate to about 0.2 mm, so no sliding fit is tighter than CLR. Check them on the test piece first.
CLR = 0.25                       # room round a motor in its pocket, and between a fork arm and its horn
ARM_IN = FACE + HORN_T + CLR     # 14.75: inner face of a fork arm. Across both horns is 29.0 mm, the gap 29.5
ARM_T = 3.0                      # ROBOTIS: M2x6 tapping screw through a 3 mm plate into the horn
ARM_OUT = ARM_IN + ARM_T         # 17.75
SEAT_UP = 0.6                    # each fork screw seats this far out from the arm: pulled tight onto the horn, an M2 x 6 then ends 0.6 mm short of the case
DISC_R = 9.5                     # fork arm disc around the shaft
WEB_R, WEB_T = 16.0, 3.5         # fork web: inner radius clears the case corner (13.8), thickness
CHK_IN = FACE + CLR              # 11.75: inner face of a pocket wall (cheek). The motor is 23.0 mm, the gap 23.5
CHK_T = 2.35                     # pocket wall: thin enough that a fork arm pulled tight onto its horn (14.5) still clears it by 0.40
CHK_OUT = CHK_IN + CHK_T         # 14.10
POCKET = MW / 2 + CLR            # 10.25: pocket floor and roof, from the motor's middle
M2_CLEAR = 1.15                  # radius of a clearance hole for an M2 tapping screw
M2_PILOT = 0.85                  # radius of the hole an M2 tapping screw cuts its thread into
CSK_R, CSK_H = 1.95, 0.85        # countersink for a flat-head M2 (3.8 head). An M2 x 5 flat-head through a pocket wall goes 2.4 mm into the case
M25_PILOT, M25_CLEAR = 1.05, 1.4 # M2.5 self-tapping into plastic: pilot and clearance radius
CSK25_R = 2.45                   # countersink for a flat-head M2.5 (4.7 head)
CENTER_R = 3.75                  # centre hole in a fork arm: the horn's 5 mm screw head passes through
LENS_H = 2.0                     # every fork arm disc is domed outward by this much: a round button over the joint
CBORE_R = 2.25                   # pocket in the dome so the screw head still seats on the 3 mm plate
KNEE_R0, KNEE_R1 = 16.3, 19.5    # round knee shell: inner and outer radius about the knee axis
KNEE_A0 = 55.0                   # where the knee shell stops, in degrees from the shin toward its outer side

# ------------------------------------------------------------------ robot geometry (same proportions as the checked model)
HIP_X, HIP_Y, HIP_Z = 58.0, 55.0, 63.0   # hip turn axis: position in plan, and mid-height of the turn motor
COXA = 30.0                      # hip turn axis to hip lift axis
L1, L2 = 60.0, 99.0              # thigh (lift axis to knee axis), shin (knee axis to foot centre)
FOOT_R = 13.5
FOOT_REACH = 36.0                # foot centre to lift axis, measured along the floor, standing
BODY_X, BODY_Y = 72.0, 69.0      # half width, half length of the head shell
Z_BELLY, Z_DECK, Z_LIDBASE, Z_TOP = 36.0, 74.5, 76.5, 138.0   # deck = 74.5 to 76.5
WALL = 1.6                       # chassis wall and belly
LW, ROOF = 1.2, 1.6              # head shell wall and roof (ribbed under the shoulder)
DECK_T = 2.0
SETBACK = 12.5                   # the chassis corner faces sit this far inside the hip turn axis
Z_NOTCH = 84.0                   # the head shell is cut away below this height over each hip
SH_Y, SH_Z = 40.0, 151.5         # shoulder axis
LA, LH = 82.5, 111.0             # upper arm, forearm to grip centre
CLAW_X, CLAW_Y = 75.0, 11.0      # claw motor shaft in the forearm frame
GRIP = 11.5                      # each finger face sits this far from the centre line when holding a 22.5 mm block
EYE_Z, EYE_R, EYE_SINK = 105.5, 21.0, 4.5            # a 41 mm dome that fills its seat
R_CORNER, TOP_CH, TOP_R = 45.0, 14.0, 26.0   # head shell: corner radius in plan; 45 degree start then a 26 mm round on the top edge
EYE_ANG = math.radians(20.0)     # each big eye sits on a flat panel turned this far outward from straight ahead
PANEL_W = 22.0                   # half width of that flat panel
TUB_R, TUB_CH, TUB_FR = 10.0, 7.0, 10.0   # chassis: round on the upright edges; 45 degree belly edge, then a round above it
CAM_Z = 94.5
SH_MOUNT = [(18.0, -27.0), (-18.0, -27.0), (6.5, 11.0), (-6.5, 11.0)]   # roof screws, relative to the shoulder axis

N45 = 1 / math.sqrt(2)
C_HIP = (HIP_X + HIP_Y) * N45    # distance of a hip axis from the centre, measured along its diagonal
C_FACE = C_HIP - SETBACK         # distance of a chassis corner face
LEGS = [(1, 1), (-1, 1), (1, -1), (-1, -1)]     # (side, front/back)

def panel(s, ang=None, w=None):
    """A flat panel cut into the round front corner of the head. Returns (n, d, P): outward normal, distance of the plane
    from the body centre line measured along n, and the point at the middle of the panel (x, y). s = +1 right, -1 left."""
    ang = EYE_ANG if ang is None else ang; w = PANEL_W if w is None else w
    n = (s * math.sin(ang), math.cos(ang))
    c = (s * (BODY_X - R_CORNER), BODY_Y - R_CORNER)
    r = math.sqrt(R_CORNER ** 2 - w ** 2)
    return n, r + n[0] * c[0] + n[1] * c[1], (c[0] + r * n[0], c[1] + r * n[1])

def panel_frame(s, z, ang=None, w=None, along=0.0):
    """Frame on a panel: z points out of the head, y is up. 'along' slides it sideways on the panel, toward the nose if negative."""
    n, d, P = panel(s, ang, w)
    tx, ty = n[1] * s, -n[0] * s                    # along the panel, away from the nose
    return frame((P[0] + along * tx, P[1] + along * ty, z), (-n[1], n[0], 0), (0, 0, 1))

def hip_frame(sx, sy, z=HIP_Z):
    """Frame at a hip turn axis: x points out along the diagonal, z up."""
    return T(sx * HIP_X, sy * HIP_Y, z) @ Rz(math.atan2(sy, sx))

# ------------------------------------------------------------------ shared features
def arm_holes(axis, a=0.0, b=0.0):
    """Tools: four M2 clearance holes on the horn circle plus the centre hole, through both fork arms and their domes.
    Each screw hole has a pocket through the dome so the head seats on the 3 mm plate."""
    top = ARM_OUT + LENS_H + 1
    seat = ARM_OUT + SEAT_UP
    tools = [cyl(axis, a, b, CENTER_R, -top, top), cyl(axis, a, b, CENTER_R + 0.55, seat, top), cyl(axis, a, b, CENTER_R + 0.55, -top, -seat)]   # wider through the dome, so it merges with the screw pockets
    for k in range(4):
        x, y = a + PCD_R * math.cos(k * math.pi / 2), b + PCD_R * math.sin(k * math.pi / 2)
        tools += [cyl(axis, x, y, M2_CLEAR, -top, top), cyl(axis, x, y, CBORE_R, seat, top), cyl(axis, x, y, CBORE_R, -top, -seat)]
    return tools

def arm_domes(axis, a=0.0, b=0.0):
    """The two shallow domes on the outer faces of a fork's arms, each on a SEAT_UP disc that carries the screw seats."""
    r = DISC_R - 0.4
    return [cyl(axis, a, b, r, ARM_OUT - 0.1, ARM_OUT + SEAT_UP), lens(axis, a, b, ARM_OUT + SEAT_UP, 1, r, LENS_H - SEAT_UP),
            cyl(axis, a, b, r, -ARM_OUT - SEAT_UP, -ARM_OUT + 0.1), lens(axis, a, b, -ARM_OUT - SEAT_UP, -1, r, LENS_H - SEAT_UP)]

def cheek_hole(axis, a, b, outer, sign):
    """Tools: an M2 clearance hole with a countersink on the outer face of a cheek. 'outer' is the face position, sign its side."""
    inner = outer - sign * 4.0
    lo, hi = sorted((inner, outer + sign * 0.05))
    hole = cyl(axis, a, b, M2_CLEAR, lo, hi)
    if sign > 0:
        csk = cone(axis, a, b, M2_CLEAR, CSK_R, outer - CSK_H, outer + 0.01)
    else:
        csk = cone(axis, a, b, CSK_R, M2_CLEAR, outer - 0.01, outer + CSK_H)
    return [hole, csk]

def idler_cheek_cuts(L, y0=-CHK_OUT - 0.1, y1=-CHK_IN + 0.1):
    """Tools for the idler-side cheek of a pocket whose motor sits at x = L with its head toward +x and its idler toward -y.
    The cheek stops short of the two sockets, and a channel down its middle takes the wires back past the motor's tail.
    The wires lie in the 3 mm layer between the case and the next link's fork arm."""
    return [box(L + PLUG_END, L - 10.9, y0, y1, -10.2, 10.2),                      # both sockets open
            box(L - TAIL - 4.0, L + PLUG_END + 0.1, y0, y1, -WIRE_W / 2, WIRE_W / 2)]   # wire channel, into the space behind the tail

# ------------------------------------------------------------------ leg parts
def link(L, floor=1, bulge=4.0, roof=None):
    """Thigh / upper arm. Fork on the motor at the origin (axis = y), pocket for the next motor at x = L.
    The closed side of the pocket is +z (floor=1) or -z (floor=-1) and is rounded outward by 'bulge'.
    roof = (start x, bulge) closes the other side too, so the link is a soft tube and the motor slides in from the end.
    A tube prints standing on its open end; without a roof it prints open side down."""
    p = []
    rx1 = (roof[2] if roof and len(roof) > 2 else L - 11)                          # where the cover ends
    for s in (1, -1):
        y0, y1 = sorted((s * ARM_IN, s * ARM_OUT))
        p += [cyl('y', 0, 0, DISC_R, y0, y1), box(0, WEB_R + WEB_T, y0, y1, -8, 8), box(-4, WEB_R + WEB_T, y0, y1, -10, 0)]
        c0, c1 = sorted((s * CHK_IN, s * CHK_OUT))
        p.append(box(WEB_R + WEB_T, L - 11, c0, c1, -10, 12.6))
        if roof:
            p.append(box(roof[0], rx1, c0, c1, -12.6, -10))
            g = WEB_R + WEB_T                                                     # 45 degree ease under the fork arm, for printing on end
            p.append(cq.Workplane("XY").polyline([(g - 0.1, s * (CHK_OUT - 0.1)), (g - 0.1, s * ARM_OUT), (g + ARM_OUT - CHK_OUT, s * (CHK_OUT - 0.1))]).close().extrude(18).translate((0, 0, -10)))
    p += arm_domes('y')
    p.append(box(WEB_R, WEB_R + WEB_T, -ARM_OUT, ARM_OUT, -10, 9))               # web, full width
    p.append(box(WEB_R, WEB_R + WEB_T, -CHK_OUT, CHK_OUT, 9, 12.6))              # web, up to the floor
    p.append(box(WEB_R, L - 11, -CHK_OUT, CHK_OUT, POCKET, 12.6))                # floor of the pocket
    p.append(arch('x', CHK_OUT, 12.55, bulge, WEB_R, L - 11))                     # rounded back
    if roof:
        p.append(box(roof[0], rx1, -CHK_OUT, CHK_OUT, -12.6, -POCKET))        # roof
        p.append(arch('x', CHK_OUT, 12.55, roof[1], roof[0], rx1).mirror("XY"))
    body = union(*p)
    tools = arm_holes('y')
    for s in (1, -1):
        for z in (HOLE_X, -HOLE_X):
            tools += cheek_hole('y', L - HOLE_TAIL, z, s * CHK_OUT, s)
    tools.append(box(WEB_R - 0.1, WEB_R + WEB_T + 0.1, -5, 5, -8, -1))            # cable slot through the web
    tools += idler_cheek_cuts(L)
    if roof and rx1 < L - 11 - 0.1:                                               # a cover that stops short starts at 45 degrees, so it prints on end
        tools.append(cq.Workplane("XZ").polyline([(rx1 + 0.1, -POCKET), (rx1 + 0.1, -20.0), (rx1 - 9.75, -20.0)]).close().extrude(2 * CHK_OUT + 2).translate((0, CHK_OUT + 1, 0)))
    out = cut(body, *tools)
    return out if floor > 0 else out.mirror("XY")

THIGH_ROOF = (24.0, 2.0)         # where the thigh's cover starts, and how far it bulges
ARM_ROOF = (26.0, 3.0, 46.0)      # the upper arm's cover stops short, so the forearm can still fold onto it

def thigh():
    return link(L1, floor=-1, bulge=2.5, roof=THIGH_ROOF)     # open side up and in, so the thigh can lift past vertical

PAD_A, PAD_B, PAD_M = (-3.0, 19.4), (52.0, 11.5), (26.0, 17.5)   # shin pad, side view: start on the knee, end at the boot, a point in between
PAD_ROUND = 53.1                 # the pad is also rounded from side to side, on this radius

def shin():
    """Fork on the knee motor (axis = y at the origin), a soft pad down the outside of the leg, and a boot that narrows to the foot peg at x = L2.
    The pad runs over the knee and closes the gap between the two arms, on the outer side only: the thigh still folds in from the inner side.
    The web sits behind the knee so the leg can fold. Prints standing on its heel (the -x face), with a brim."""
    p, cover = [], []
    def side(y0, y1, pts):                                                         # the pad's side view, pulled across from y0 to y1
        w = cq.Workplane("XZ").moveTo(*PAD_A).threePointArc(PAD_M, PAD_B)
        for q in pts: w = w.lineTo(*q)
        return w.close().extrude(y1 - y0).translate((0, y1, 0))
    for s in (1, -1):
        y0, y1 = sorted((s * ARM_IN, s * ARM_OUT))
        p += [cyl('y', 0, 0, DISC_R, y0, y1), box(-WEB_R - WEB_T, 14, y0, y1, -7, DISC_R), box(13, 52, y0, y1, -4.5, DISC_R)]
        cover.append(sector(KNEE_R1, KNEE_A0, 180.0, y0, y1))                     # the arm grows out to meet the pad
        cover.append(side(y0, y1, [(52.0, DISC_R - 0.1), (-3.0, DISC_R - 0.1)]))
    p += arm_domes('y')
    a0 = math.radians(KNEE_A0)
    cover.append(sector(KNEE_R1, KNEE_A0, 180.0, -ARM_OUT, ARM_OUT, r_in=KNEE_R0))   # over the knee
    cover.append(side(-ARM_OUT, ARM_OUT, [(52.0, DISC_R - 0.1), (46.0, DISC_R - 0.1), (KNEE_R0 * math.cos(a0), KNEE_R0 * math.sin(a0)), (0.0, KNEE_R0 + 0.5)]))   # down the shin
    lip = cq.Workplane("XZ").polyline([(-WEB_R - WEB_T, 7.5), (-13.79, 13.79), (-13.79, 7.5)]).close().extrude(2 * ARM_OUT).translate((0, ARM_OUT, 0))
    cover.append(lip)                                                             # eases the start of the pad to 45 degrees
    slope = math.degrees(math.atan2(PAD_A[1] - PAD_B[1], PAD_B[0] - PAD_A[0]))
    rounder = cyl('x', 0, -PAD_ROUND, PAD_ROUND, -80, 120).rotate((0, 0, 0), (0, 1, 0), slope).translate((PAD_A[0], 0, PAD_A[1] + 1.5))
    pad = union(*cover).intersect(rounder).cut(cyl('y', 0, 0, KNEE_R0, -ARM_IN, ARM_IN))   # round it side to side; keep the knee motor's space clear
    p.append(pad)
    p.append(box(-WEB_R - WEB_T, -WEB_R, -ARM_OUT, ARM_OUT, -7, DISC_R))         # heel web: also the face it prints on
    p.append(box(46, 52, -ARM_OUT, ARM_OUT, -4.5, DISC_R))                        # bridge where the two arms meet
    for s in (1, -1):                                                              # 45 degree gussets: shorter bridge when printed standing
        p.append(cq.Workplane("XY").polyline([(46 - GUS, s * ARM_IN), (46.1, s * ARM_IN), (46.1, s * (ARM_IN - GUS))]).close().extrude(DISC_R + 4.5).translate((0, 0, -4.5)))
    boot = (cq.Workplane("YZ").workplane(offset=51).center(0, 2.5).rect(2 * ARM_OUT, DISC_R + 4.5)
            .workplane(offset=14).center(0, -1.0).ellipse(13.5, 7.5)
            .workplane(offset=20).center(0, -1.5).circle(6.5).loft(combine=True))
    p += [boot, box(L2 - 15, L2 + 2, -PEG / 2, PEG / 2, -PEG / 2, PEG / 2)]       # square peg: the foot cannot turn on it
    return cut(union(*p), *arm_holes('y'))

PEG = 9.0                        # side of the square foot peg
FOOT_GRIP = 0.1                  # the foot's socket is this much smaller than the peg on each side: it stretches on
GUS = 6.0                        # size of the gussets under the shin's bridge

def foot():
    """Soft foot (print in TPU). Ball centre at the origin; pushes onto the shin peg from -x. Prints flat face down."""
    R, k = FOOT_R, math.sqrt(0.5)
    s = cq.Workplane("XY").moveTo(-7, 0).lineTo(-7, R).lineTo(0, R).threePointArc((R * k, R * k), (R, 0)).close().revolve(360, (0, 0, 0), (1, 0, 0))
    g = PEG / 2 - FOOT_GRIP
    return s.cut(box(-8, 2.2, -g, g, -g, g))

def hip():
    """Hip bracket. Fork on the turn motor (axis = z at the origin), pocket for the lift motor hanging tail-down at x = COXA.
    Prints on its side."""
    p = []
    for s in (1, -1):
        z0, z1 = sorted((s * ARM_IN, s * ARM_OUT))
        p += [cyl('z', 0, 0, DISC_R, z0, z1), box(0, 18.5, -CHK_OUT, CHK_OUT, z0, z1)]
        c0, c1 = sorted((s * CHK_IN, s * CHK_OUT))
        p.append(box(18.5, COXA + 10.3, c0, c1, -27, -11.5))                     # cheeks on the lift motor's tail
        r0, r1 = sorted((s * 8.6, s * CHK_IN))
        p.append(box(18.5, COXA - POCKET, r0, r1, -TAIL - CLR, -11.5))           # ribs that seat the motor's back face
    p += arm_domes('z')
    p.append(box(15, 18.5, -CHK_OUT, CHK_OUT, -27, ARM_OUT))                     # back web
    p.append(box(18.5, COXA + 10.3, -CHK_OUT, CHK_OUT, -27, -TAIL - CLR))        # floor under the tail
    body = union(*p)
    tools = arm_holes('z')
    for s in (1, -1):
        for x in (COXA - HOLE_X, COXA + HOLE_X):
            tools += cheek_hole('y', x, -HOLE_TAIL, s * CHK_OUT, s)
    tools.append(box(14.9, 18.6, -8.5, 8.5, -21, -5))                            # cable window behind the lift motor
    tools.append(box(18.4, COXA + 10.4, -CHK_OUT - 0.1, -CHK_IN + 0.1, PLUG_END, -11.4))   # the idler-side cheek stops below the two sockets
    tools.append(box(14.9, COXA - MW / 2 + 0.1, -CHK_OUT - 0.1, -8.4, PLUG_END, PLUG_Y1 + 0.3))   # the window reaches the inner socket, so its wire goes straight back to the turn motor
    tools.append(cq.Workplane("XZ").polyline([(COXA + 10.4, -27.1), (COXA + 10.4, -23.6), (COXA + 6.4, -27.1)]).close().extrude(40).translate((0, 20, 0)))   # ease the bottom front corner so the shin can swing under
    tools.append(cq.Workplane("XZ").polyline([(18.6, ARM_OUT - 4.5), (18.6, ARM_OUT + 0.1), (14.0, ARM_OUT + 0.1)]).close().extrude(40).translate((0, 20, 0)))   # ease the top corner so the thigh can lift past vertical
    return cut(body, *tools)

# ------------------------------------------------------------------ arm parts
def upper_arm():
    return link(LA, bulge=4.0, roof=ARM_ROOF)

def soft_prism(pts, z0, z1, r_side=3.0, r_top=2.5, keep_y=None):
    """A finger: polygon in plan with every corner rounded, extruded, top edge rounded where the kernel allows.
    With keep_y, the side at y = keep_y stays square (that face lies on the print bed)."""
    if keep_y is not None:
        pts = [(x, y + 12.0) if abs(y - keep_y) < 1e-6 else (x, y) for x, y in pts]
    w = cq.Workplane("XY").polyline(pts).close().offset2D(-r_side).offset2D(r_side).extrude(z1 - z0)
    if keep_y is not None:
        w = w.intersect(box(-500, 500, -500, keep_y, -1, z1 - z0 + 1))
    for r in ([r_top, r_top * 0.6] if r_top > 0 else []):
        try:
            f = w.faces(">Z").edges().fillet(r)
            if f.val().isValid(): w = f; break
        except Exception:
            pass
    return w.translate((0, 0, z0))

def forearm():
    """Fork on the elbow motor (axis = y at the origin), neck, palm that holds the claw motor (axis = z), and the fixed finger.
    Prints flat on its -z face."""
    zb = -CHK_OUT
    p = []
    for s in (1, -1):
        y0, y1 = sorted((s * ARM_IN, s * ARM_OUT))
        p += [cyl('y', 0, 0, DISC_R, y0, y1), box(0, WEB_R + WEB_T, y0, y1, -8, 8), box(-4, WEB_R + WEB_T, y0, y1, zb, 0)]
    p += arm_domes('y')
    p.append(box(WEB_R, WEB_R + WEB_T, -ARM_OUT, ARM_OUT, zb, 9))                # web
    p.append(box(WEB_R, 64, -19, CLAW_Y + 12, zb, -CHK_IN))                      # bottom plate: neck and lower cheek
    p.append(box(WEB_R, 64, CLAW_Y - POCKET - 3.0, CLAW_Y - POCKET, zb, CHK_IN)) # spine along the motor
    p.append(box(38, 50, CLAW_Y - 16.2, CLAW_Y - POCKET, zb, CHK_IN))            # boss for the palm cap screw
    p.append(soft_prism([(56, -20), (92, -20), (121, -15.6), (120, -GRIP), (56, -GRIP)], zb, 8.0, r_side=2.0))   # chubby fixed finger
    body = union(*p)
    tools = arm_holes('y')
    for y in (CLAW_Y - HOLE_X, CLAW_Y + HOLE_X):                                  # claw motor screws, from underneath
        tools += cheek_hole('z', CLAW_X - HOLE_TAIL, y, zb, -1)
    tools.append(cyl('z', 44, CLAW_Y - 13.2, M25_PILOT, CHK_IN - 9, CHK_IN + 0.1))
    tools.append(box(WEB_R - 0.1, WEB_R + WEB_T + 0.1, 2, 12, -6, 2))            # cable slot through the web
    tools.append(box(CLAW_X + PLUG_END, 64.1, CLAW_Y - MW / 2 - 0.3, CLAW_Y + 12.1, zb - 0.1, -CHK_IN + 0.1))            # the bottom plate stops short of the claw motor's two sockets
    tools.append(box(CLAW_X - TAIL - 4.0, CLAW_X + PLUG_END + 0.1, CLAW_Y - WIRE_W / 2, CLAW_Y + WIRE_W / 2, zb - 0.1, -CHK_IN + 0.1))   # wire channel back past the motor's tail
    return cut(body, *tools)

def palm_cap():
    """Plate over the claw motor: two motor screws and one screw into the forearm. Frame = forearm frame."""
    body = box(38, 64, CLAW_Y - 16.2, CLAW_Y + 12, CHK_IN, CHK_OUT)
    tools = []
    for y in (CLAW_Y - HOLE_X, CLAW_Y + HOLE_X):
        tools += cheek_hole('z', CLAW_X - HOLE_TAIL, y, CHK_OUT, 1)
    tools.append(cyl('z', 44, CLAW_Y - 13.2, M25_CLEAR, CHK_IN - 0.1, CHK_OUT + 0.1))
    return cut(body, *tools)

def finger():
    """Moving finger. Fork on the claw motor (axis = z at the origin), chubby blade forward. Prints on its +y face."""
    p = []
    for s in (1, -1):
        z0, z1 = sorted((s * ARM_IN, s * ARM_OUT))
        p += [cyl('z', 0, 0, DISC_R, z0, z1), box(0, WEB_R + WEB_T, -8, DISC_R, z0, z1)]
    p += arm_domes('z')
    p.append(box(WEB_R, WEB_R + WEB_T, -8, DISC_R, -ARM_OUT, ARM_OUT))
    p.append(soft_prism([(WEB_R + 1, GRIP - CLAW_Y), (43.5, GRIP - CLAW_Y), (47, GRIP - CLAW_Y + 4), (37, DISC_R), (WEB_R + 1, DISC_R)], -10.5, 10.5, r_side=2.5, r_top=0, keep_y=DISC_R))
    return cut(union(*p), *arm_holes('z'))

COWL_Y = -21.0                   # front edge of the cowl's top, relative to the shoulder axis

def shoulder_mount():
    """Rounded cowl on the roof. It holds the shoulder motor flat, tail to the rear; the motor slides in from the front.
    Frame: origin on the shoulder axis, robot axes. Prints base down: the rounded top bridges across."""
    zb = -(SH_Z - Z_TOP)                                                          # roof surface
    p = [box(-22, 22, -31, -4, zb, -POCKET), box(-12, 12, -5, 14.5, zb, -POCKET)]
    for s in (1, -1):
        c0, c1 = sorted((s * CHK_IN, s * CHK_OUT))
        p.append(box(c0, c1, -28.2, -11.5, zb, 12.6))
    p.append(box(-CHK_OUT, CHK_OUT, -28.2, -TAIL - CLR, zb, 12.6))                # back wall
    p.append(box(-CHK_OUT, CHK_OUT, -28.2, COWL_Y, POCKET, 12.6))                 # top over the motor's tail
    p.append(arch('y', CHK_OUT, 12.55, 3.0, -28.2, COWL_Y))                       # rounded over
    body = union(*p)
    tools = []
    for s in (1, -1):
        for z in (HOLE_X, -HOLE_X):
            tools += cheek_hole('x', -HOLE_TAIL, z, s * CHK_OUT, s)
    for k, (x, y) in enumerate(SH_MOUNT):
        tools.append(cyl('z', x, y, M25_CLEAR, zb - 0.1, -POCKET + 0.1))
        if k >= 2:                                                                # the two front screws lie under the motor: flat heads, sunk flush
            tools.append(cone('z', x, y, M25_CLEAR, CSK25_R, -POCKET - (CSK25_R - M25_CLEAR), -POCKET + 0.01))
    tools.append(box(-5, 5, -28.3, -24.6, -8.0, 6.0))                             # window in the back wall
    tools.append(box(-CHK_OUT - 0.1, -CHK_IN + 0.1, PLUG_END, -11.4, zb + 3.3, 12.7))                                   # the idler-side cheek stops short of the two sockets
    tools.append(box(-CHK_OUT - 0.1, -CHK_IN + 0.1, -28.3, PLUG_END + 0.1, -WIRE_W / 2, WIRE_W / 2))                    # wire channel along the cheek and out through the back, next to the roof's cable hole
    return cut(body, *tools)
