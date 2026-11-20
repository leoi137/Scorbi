# Cybi

Cybi is an open-source robot: a small scorpion spider with four legs, an arm and a claw, moved by 15 Feetech servos. Its hardware design, simulation model and build guide are all here, under open licenses.

It is not built yet. Nothing has been printed, wired or switched on. You can try it in a physics simulation at [myautonomylab.com](https://www.myautonomylab.com).

## Status

- **CAD and simulation model: v0.4.** The CadQuery scripts in `cad/` and the model in `scorpion/` are v0.4.
- **Build pack: v0.5.** Three reviews found 52 problems in v0.4, five of them dangerous. v0.5 fixes them, and `build-pack/` says how: the findings, how to print, wire, build and test it, and what only a real build can prove. The v0.5 CAD files and shopping list it mentions are not in this repository yet.

Don't build v0.4 from the files here. Wait for the v0.5 CAD.

## What's here

| Path | What |
|---|---|
| `build-pack/` | The v0.5 build pack. Download the repository and open `build-pack/index.html` in a browser. |
| `cad/` | The v0.4 CadQuery scripts. Every size is a named number in `cad/parts.py` and `cad/body.py`. Run on their own, they write print files and check results to `out/`, which is not committed. To use the motor maker's own 3D model, download Feetech's STEP file for the HD-1910-C001 and put it in `cad/` (see `cad/vendor.py`). |
| `build_model.py` | Turns the CAD into the model files below. |
| `check_model.py` | Loads the model in MuJoCo and checks it against the CAD: feet, mass, standing, a drop. |
| `scorpion/scorpion.xml` | MJCF of the robot alone. |
| `scorpion/scene.xml` | The robot on a flat floor, for MuJoCo's viewer. |
| `scorpion/scorpion.urdf` | The same robot as URDF. |
| `scorpion/model.json` | Joint ranges, the standing pose and the motor settings. |
| `scorpion/meshes/` | One STL per part, in metres, in the part's own frame. |

## Licenses

| What | License |
|---|---|
| The hardware design: `cad/` and `scorpion/` | [CERN-OHL-S-2.0](LICENSES/CERN-OHL-S-2.0.txt) |
| The software: `build_model.py` and `check_model.py` | [Apache-2.0](LICENSES/Apache-2.0.txt) |
| The documentation: `build-pack/` and this README | [CC-BY-4.0](LICENSES/CC-BY-4.0.txt) |

If you make and share a changed version of the hardware, CERN-OHL-S asks you to share your changed design files under the same license.

The name Cybi is not covered by these licenses.

## Rebuild after a CAD change

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build_model.py      # about 50 s
.venv/bin/python check_model.py
.venv/bin/python -m mujoco.viewer --mjcf scorpion/scene.xml
```

`build_model.py` overwrites everything in `scorpion/`. Don't edit those files by hand.

## Frames and joints

- **Frame:** x forward, y left, z up. Metres and radians.
- **Base origin:** on the body's centre line, at the height of the hip turn motors. It sits 73.5 mm above the floor when standing.
- **Joint order:** the names and order below are fixed: the website's simulator depends on them. MuJoCo uses this order. Isaac Lab orders joints its own way, so map them by name.

| Joints | Zero | Positive | Range |
|---|---|---|---|
| `fl/fr/rl/rr_hip_turn` | leg along its 45 degree diagonal | turns about up (counter-clockwise seen from above) | -60 to 60 degrees |
| `*_hip_lift` | thigh level | raises the knee | -15 to 95 degrees |
| `*_knee` | leg straight | bends the shin down | 75 to 155 degrees |
| `arm_shoulder` | upper arm level, forward | raises it | -5 to 100 degrees |
| `arm_elbow` | forearm in line | bends it up | -110 to 0 degrees |
| `claw` | fingers parallel, 23 mm apart | opens | -25 to 53 degrees |

- **Knee angle:** the CAD measures the knee as the angle between thigh and shin, so the CAD's knee angle is 180 degrees minus this one. The ranges above are the collision-free ranges from the CAD sweeps.
- **Standing pose:** in `model.json`: hip lift 0.708, knee 2.376, shoulder 1.25, elbow -1.80.
- **Feet:** the feet are fixed bodies named `fl_foot`, `fr_foot`, `rl_foot` and `rr_foot`. Each has a 13.5 mm sphere for contact, so Isaac Lab's contact sensors and foot rewards can name them.
- **Mass:** the mass is 1050 g, matching the CAD pack's estimate. Printed parts (499 g) and motors (21 g each) are placed where they are. The electronics sit as boxes in the base: the 2S pack in the belly door, the charge board at the back wall, and the boards on the deck. The 68 g left over (screws, wires, switch and fuse) is spread over the deck.
- **Collisions:** shapes are simple: boxes for the body, capsules for the links, spheres for the feet and boxes for the claw. Self-collision is off.

## Motors

Feetech HD-1910-C001, running straight off the 2S pack (6.0 to 8.4 V). The model uses its 6 V figures, the low end of the pack: 1.18 N m (12 kg cm) stall torque and 9.6 rad/s (92 rpm) with no load. The model drives each joint with a position controller:

| | MuJoCo | Isaac Lab |
|---|---|---|
| stiffness | `kp` 9.0 N m/rad | `stiffness=9.0` |
| damping | `kv` 0.12, plus joint damping 0.05 | `damping=0.17` |
| torque limit | `forcerange` +-1.18 | `effort_limit_sim=1.18` |
| speed limit | none | `velocity_limit_sim=9.6` |
| armature | 0.002 | `armature=0.002` |
| friction | `frictionloss` 0.02 | `friction=0.02` |

These are estimates, not measurements. The damping is the motor's own back-EMF (1.18 / 9.6). The stiffness is the v0.3 estimate scaled by the stall torque (4.0 x 1.18 / 0.52), as if the same position loop drove the stronger motor. With these numbers the scripted gait tracks within about 1.5 degrees, and its busiest motor stays under 60% of stall. The published figures don't agree: Feetech's product page gives 9 kg cm and 73 rpm at 4.8 V, its wiki 10 kg cm and 110 rpm, and resellers 12 kg cm and 92 rpm at 6 V. Measure one motor before trusting any of them. Whatever you train with, the website must match it. If you change these numbers, change `MOTOR` in `build_model.py` and rebuild. Randomize stiffness, friction and mass by +-20 to 30% in training so the policy doesn't depend on them.

The physics runs at 500 Hz (`timestep` 0.002). Control runs at 50 Hz.

## Training in Isaac Lab

- **Import:**
  - Either importer works.
  - For URDF, use `fix_base=False` and `merge_fixed_joints=False`, otherwise the foot bodies disappear into the shins.
  - For MJCF, import `scorpion/scorpion.xml`.
- **Initial state:** start from `model.json`: base height 0.0735 m, joint positions from `stand.joints`.
- **Control rate:** 50 Hz, for example sim `dt=0.005` with `decimation=4`.
- **Commands:** use the heading command (`heading_command=True`, stiffness 0.5). The website steers by heading too. This robot is small: the scripted gait walks about 0.08 m/s. Start command ranges around +-0.1 m/s forward, +-0.06 m/s sideways and +-1 rad/s turning.
- **Terrain:** the website's terrain is gentle. Bumps go up to 12 mm, a ledge is 8 mm and a ridge is 6 mm. Train on Isaac Lab's terrain generator at the same scale, for example random rough 0 to 10 mm and boxes 5 to 10 mm. The default rough terrain is sized for a robot ten times this one.
- **Observations:**
  - The website builds the standard velocity-task observations: `base_lin_vel`, `base_ang_vel`, `projected_gravity`, `velocity_commands`, `joint_pos_rel`, `joint_vel_rel` and `last_action`.
  - Leave out `height_scan`; the website can't build it yet.
  - Noise and corruption only apply in training, so they don't matter here.
