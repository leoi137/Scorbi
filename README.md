# Robot model

The scorpion spider v0.4 as a simulation model, generated from its CAD. The website runs this model in MuJoCo; train on the same model in Isaac Lab.

| Path | What |
|---|---|
| `cad/` | The v0.4 CadQuery scripts, unchanged from the CAD pack. Every size is a named number in `cad/parts.py` and `cad/body.py`. Run on their own, they write print files and check results to `robot/out/`, which is not committed. |
| `build_model.py` | Turns the CAD into the model files below. |
| `check_model.py` | Loads the model in MuJoCo and checks it against the CAD: feet, mass, standing, a drop. |
| `scorpion/scorpion.xml` | MJCF of the robot alone. |
| `scorpion/scene.xml` | The robot on a flat floor, for MuJoCo's viewer. |
| `scorpion/scorpion.urdf` | The same robot as URDF. |
| `scorpion/model.json` | Joint ranges, the standing pose and the motor settings. |
| `scorpion/meshes/` | One STL per part, in metres, in the part's own frame. |
| `../public/sim/robot/` | The MJCF again with lighter meshes, for the website. `scripts/bake-sim.ts` turns it into what the page actually loads (see below). |

## Rebuild after a CAD change

```
python3 -m venv .venv && .venv/bin/pip install -r robot/requirements.txt
.venv/bin/python robot/build_model.py      # about 50 s
.venv/bin/python robot/check_model.py
.venv/bin/python -m mujoco.viewer --mjcf robot/scorpion/scene.xml
```

`build_model.py` overwrites everything in `scorpion/` and `public/sim/robot/`. Don't edit those files by hand.

The website doesn't load `public/sim/robot/` directly. `scripts/bake-sim.ts` precompiles the physics model to MuJoCo's `.mjb`, simplifies the meshes and works out their normals, and records the dance loop the page shows while the simulator loads. It writes `public/sim/robot.bin`, `sim.bin` and `mujoco.wasm`, which are not committed. `next.config.ts` runs it whenever Next starts a dev server or a build, however Next is started, and it returns at once when nothing it reads (this model, `src/sim/`, the MuJoCo and three.js versions) has changed. So after a CAD change, or a change to the controller or the physics setup, restarting `npm run dev` or building is enough. A bake whose checks fail stops the build; the dev server keeps the last good files and warns. `npm run bake -- --force` rebakes by hand. It needs Node 22.18 or later.

## Frames and joints

- **Frame:** x forward, y left, z up. Metres and radians.
- **Base origin:** on the body's centre line, at the height of the hip turn motors. It sits 73.5 mm above the floor when standing.
- **Joint order:** the names and order below are the contract in `src/sim/spec.ts`. MuJoCo uses this order. Isaac Lab orders joints its own way; see "Drop in a policy".

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

## Drop in a policy

Isaac Lab's rsl_rl play script writes `logs/rsl_rl/<run>/exported/policy.onnx`.

1. Copy that file to `public/sim/policy/policy.onnx`.
2. In `public/sim/policy/policy.json`, set `"onnx": "policy.onnx"` and check the fields below against the run's `params/env.yaml`.
3. Run the site. If the policy loads, it drives the legs whenever the robot is walking or standing. Sit, bow, dance and grab still take the legs while they play.

If the policy can't be used, the console says why (`[policy] not used`) and the scripted gait keeps walking.

| Field | What to put there |
|---|---|
| `action_joints` | The joints the action term drives, in Isaac Lab's order. Print `env.unwrapped.scene["robot"].joint_names` and keep the leg joints. Isaac Lab groups joints by depth, so the template lists all hip turns, then all hip lifts, then all knees. |
| `observation_joints` | Joints in `joint_pos_rel` and `joint_vel_rel`, in order. If the observation covers every joint (the default), this list includes the arm joints in Isaac Lab's order. |
| `default_joint_pos` | The `init_state` joint positions. |
| `action_scale` | `actions.joint_pos.scale` (0.25 for Isaac Lab's velocity tasks). |
| `clip_actions` | rsl_rl's `clip_actions`, if set. |
| `observations` | The policy group's terms, in order. Give a term a scale with `{"name": "base_ang_vel", "scale": 0.25}` if the env scales it. |
| `command_limits` | `commands.base_velocity.ranges`. |
| `control_dt` | sim `dt` times `decimation`. It must be 0.02. |

The website runs the policy with a small built-in ONNX reader, not onnxruntime. It handles what rsl_rl exports (linear layers, activations, the observation normalizer) and rejects anything else by name. An LSTM policy would need onnxruntime-web added.
