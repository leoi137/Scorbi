"""Bought parts as simple solids, for fit and collision checks and for the pictures. Millimetres."""
import os
from prim import *
from parts import *
from body import (RADXA, ADAPTER, REG_B, IMU, SPK_Z, PACK_Z, HUB, HUB_Z, HUB_BAY, HUB_T, HUB_FLOOR, WAGO,
                  SHELF_Z, MIC, SWITCH, SWITCH_PANEL_Y)

def motor():
    """Feetech HD-1910-C001 in its own frame: shaft along z, driven horn at +z, idler horn at -z, head end at +y.
    Case, both horns and their screw heads, the two socket notches on the idler face, and a stub where each plug and its wires sit."""
    case = box(-MW / 2, MW / 2, -TAIL, HEAD, -FACE, FACE)
    p = [cyl('z', 0, 0, HORN_R, FACE - 0.01, FACE + HORN_T), cyl('z', 0, 0, HORN_R, -FACE - HORN_T, -FACE + 0.01),
         cyl('z', 0, 0, 2.5, FACE + HORN_T - 0.01, FACE + HORN_T + 0.8), cyl('z', 0, 0, 2.5, -FACE - HORN_T - 0.4, -FACE - HORN_T + 0.01)]
    for s in (1, -1):
        x0, x1 = sorted((s * PLUG_X0, s * (PLUG_X1 + 0.1)))
        case = case.cut(box(x0, x1, PLUG_Y0, PLUG_Y1, -FACE - 0.1, -FACE + PLUG_DEEP))                 # notch, open to the side and to the idler face
        a, b = sorted((s * 5.1, s * 8.7))
        p.append(box(a, b, -12.65, -4.85, -FACE + 2.55, -FACE + PLUG_DEEP + 0.1))                       # socket, mouth 2.55 mm inside the face
        a, b = sorted((s * 5.6, s * 8.4))
        p.append(box(a, b, -12.2, -6.3, -FACE - 2.9, -FACE + 2.6))                                      # plug and the bend of its wires: keep this clear
    return union(case, *p)

STEP_PATH = os.environ.get('HD1910_STEP', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'HD-1910-C001-20260902.stp'))   # Feetech's file: download it from their wiki and put it here
def motor_real():
    """Feetech's own STEP model, moved into the motor frame above (their origin is 8 mm toward the horn from mid-depth). None if the file is not there."""
    if not os.path.exists(STEP_PATH): return None
    return cq.importers.importStep(STEP_PATH).translate((0, 0, 8.0))

# The bought parts of v0.5 (build-pack/, shopping list and wiring page), in grams. Maker figures where they exist.
# Sizes marked "guess" have no maker drawing; the build pack lists them under "Drawn from a guess".
MASS = dict(motor=21.0, pack=108.0, radxa=16.0, adapter=16.0, reg_b=10.0, imu=1.5, camera=3.0, speaker=15.0,
            sound_card=8.0, usb_hub=12.0, fuses=30.0, hub=30.0, switch=25.0, main_fuse=10.0, alarm=8.0)
PACK = (38.0, 72.0, 19.5)        # ZOHD Lionpack 2S 3500 mAh: width, length, height. The bay takes up to 43 x 74 x 24
REG_SIZE = (14.0, 42.0, 9.0)     # Hobbywing UBEC 3A with its leads' sleeves: across, along, height (guess)
SWITCH_BODY = (16.6, 25.0, 22.0) # Cole Hersee 5582 behind the panel: across, depth, height, with its two screw terminals (guess)

def electronics():
    """name -> solid in the robot frame."""
    zt = Z_LIDBASE
    e = {}
    w, l, h = PACK
    e['pack'] = box(-w / 2, w / 2, -l / 2, l / 2, PACK_Z, PACK_Z + h)
    rb = zt + 4.0                                                                                       # Radxa Zero 3W on its 4 mm posts
    e['radxa'] = union(box(RADXA[0] - 32.5, RADXA[0] + 32.5, RADXA[1] - 15, RADXA[1] + 15, rb, rb + 1.2),
                       box(RADXA[0] - 7, RADXA[0] + 7, RADXA[1] - 4, RADXA[1] + 10, rb + 1.2, rb + 7.2),      # heatsink on the big chip
                       box(RADXA[0] - 25.4, RADXA[0] + 25.4, RADXA[1] - 14.6, RADXA[1] - 9.5, rb + 1.2, rb + 9.7))   # 40-pin header along the back edge, with the Qwiic SHIM on pins 1 to 6
    e['adapter'] = box(ADAPTER[0] - 21, ADAPTER[0] + 21, ADAPTER[1] - 16.5, ADAPTER[1] + 16.5, zt + 3.0, zt + 18.5)   # Waveshare Bus Servo Adapter (A): 42 x 33, 15.5 tall with its jack
    a, b, c = REG_SIZE
    e['reg_b'] = box(REG_B[0] - a / 2, REG_B[0] + a / 2, REG_B[1] - b / 2, REG_B[1] + b / 2, zt, zt + c)
    e['imu'] = box(IMU[0] - 12.7, IMU[0] + 12.7, IMU[1] - 8.9, IMU[1] + 8.9, zt + 2.5, zt + 5.6)                     # Adafruit LSM6DS3TR-C: 25.4 x 17.8, on 2.5 mm posts
    # hub tray: D1 and D2 (left bay), G1 to G3 (middle), P1, P2 and P3 (right), standing wire holes up; two 1000 uF capacitors over the G-P wall
    bx, by = HUB_BAY
    L = 3 * bx + 4 * HUB_T
    zb = HUB_Z + HUB_FLOOR
    blocks = []
    for k, ways in enumerate(((5, 3), (5, 5, 5), (5, 5, 3))):
        x0 = -L / 2 + HUB_T + k * (bx + HUB_T) + 0.3
        y = HUB[1] - by / 2 + 0.3
        for n in ways:
            ww, tt, dd = WAGO[n]
            blocks.append(box(x0, x0 + ww, y, y + tt, zb, zb + dd)); y += tt
    xc = -L / 2 + 2 * bx + 2.5 * HUB_T
    for dy in (-6.0, 6.0):
        blocks.append(cyl('z', xc, HUB[1] + dy, 5.0, zb + 20.7, zb + 37.7))       # 10 x 17 mm, standing on their legs
    e['hub'] = union(*blocks)
    ys = HUB[1]                                                                                         # on the fuse shelf
    zs = SHELF_Z + 2.0
    e['usb_hub'] = box(-43.0, -13.0, 24.0, 52.0, zs, zs + 11.0)                                         # small USB-C hub (guess)
    e['fuses'] = box(8.0, 48.0, 24.0, 52.0, zs, zs + 18.0)                                              # five chain fuse holders tied three under two (guess)
    yi = BODY_Y - LW
    e['camera'] = union(box(-12.5, 12.5, yi - 6.7, yi - 5.7, CAM_Z - 9.5, CAM_Z + 14.4), box(-4.25, 4.25, yi - 5.7, yi - 1.0, CAM_Z - 4.25, CAM_Z + 4.25))   # Raspberry Pi Camera V2, 25 x 23.9
    yb = -BODY_Y + LW
    e['speaker'] = cyl('y', 0, SPK_Z, 14.0, yb + 1.2, yb + 7.4)
    zr = Z_TOP - ROOF
    e['sound_card'] = box(-MIC[0] - 9.0, -MIC[0] + 9.0, MIC[1] - 20.0, MIC[1] + 20.0, zr - 8.0, zr - 0.5)   # USB sound card, taped under the left microphone holes (guess)
    sw, sd, sh = SWITCH_BODY
    e['switch'] = union(box(SWITCH[0] - sw / 2, SWITCH[0] + sw / 2, SWITCH_PANEL_Y, SWITCH_PANEL_Y + sd, SWITCH[1] - sh / 2, SWITCH[1] + sh / 2),
                        cyl('y', SWITCH[0], SWITCH[1], 5.9, -BODY_Y - 4.0, SWITCH_PANEL_Y + 0.1))       # body inside against the boss, threaded neck through the wall
    zf = Z_BELLY + WALL
    e['main_fuse'] = box(-60.0, -36.0, -21.0, 21.0, zf, zf + 10.0)                                      # main fuse holder with BP1 and BP2, tied at the left of the belly
    e['alarm'] = box(38.0, 58.0, -20.0, 20.0, zf, zf + 10.0)                                            # low-battery alarm, tied at the right of the belly
    return e
