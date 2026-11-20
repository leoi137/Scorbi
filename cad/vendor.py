"""Bought parts as simple solids, for fit and collision checks and for the pictures. Millimetres."""
import os
from prim import *
from parts import *
from body import RADXA, ADAPTER, REG_B, IMU, SPK_Z, CHG_Z, CHG_SIZE, PACK_Z

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

# masses in grams. Maker figures where they exist; the pack, protection board, charge board and bus adapter are typical values.
MASS = dict(motor=21.0, cells=94.0, bms=5.0, radxa=13.0, hat=12.0, adapter=16.0, reg_b=2.6, imu=1.5, charger=5.0, camera=3.0, speaker=15.0, switch_fuse=6.0)
CELL = (18.6, 65.2)              # one 18650: diameter, length (Molicel P28A)
BMS = (36.0, 16.0, 3.4)          # 2S protection board lying on top of the cells: a typical size, check yours

def electronics():
    """name -> solid in the robot frame."""
    zt = Z_LIDBASE
    e = {}
    r = CELL[0] / 2
    e['cells'] = union(cyl('y', -r - 0.2, PACK_Z + r, r, -CELL[1] / 2, CELL[1] / 2), cyl('y', r + 0.2, PACK_Z + r, r, -CELL[1] / 2, CELL[1] / 2))
    e['bms'] = box(-BMS[0] / 2, BMS[0] / 2, -BMS[1] / 2, BMS[1] / 2, PACK_Z + CELL[0] + 0.3, PACK_Z + CELL[0] + 0.3 + BMS[2])
    e['radxa'] = box(RADXA[0] - 32.5, RADXA[0] + 32.5, RADXA[1] - 15, RADXA[1] + 15, zt + 6.0, zt + 7.2)
    e['hat'] = box(RADXA[0] - 32.5, RADXA[0] + 32.5, RADXA[1] - 15, RADXA[1] + 15, zt + 9.0, zt + 23.0)
    e['adapter'] = box(ADAPTER[0] - 21, ADAPTER[0] + 21, ADAPTER[1] - 16.5, ADAPTER[1] + 16.5, zt + 3.0, zt + 18.5)      # Waveshare Bus Servo Adapter (A): 42 x 33, 18.5 tall with its jack
    e['reg_b'] = box(REG_B[0] - 8.9, REG_B[0] + 8.9, REG_B[1] - 8.9, REG_B[1] + 8.9, zt, zt + 8.9)
    e['imu'] = box(IMU[0] - 12.7, IMU[0] + 12.7, IMU[1] - 8.9, IMU[1] + 8.9, zt, zt + 4.6)                            # Adafruit LSM6DS3TR-C: 25.4 x 17.8
    yi = BODY_Y - LW
    e['camera'] = union(box(-12.5, 12.5, yi - 6.7, yi - 5.7, CAM_Z - 9.5, CAM_Z + 14.5), box(-4.25, 4.25, yi - 5.7, yi - 0.2, CAM_Z - 4.25, CAM_Z + 4.25))   # OV5647 board, 25 x 24
    yw = -BODY_Y + WALL                                                                                                 # inner face of the chassis back wall
    e['charger'] = union(box(-CHG_SIZE[0] / 2, CHG_SIZE[0] / 2, yw + 0.3, yw + 0.3 + CHG_SIZE[1], CHG_Z, CHG_Z + 1.6),
                         box(-4.5, 4.5, yw - 0.9, yw + 7.0, CHG_Z + 1.6, CHG_Z + 4.9))                                  # 2S USB-C charge board and its socket
    yb = -BODY_Y + LW
    e['speaker'] = cyl('y', 0, SPK_Z, 14.0, yb + 1.2, yb + 7.4)
    return e
