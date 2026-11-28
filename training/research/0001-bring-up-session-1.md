# 0001 · Bring-up on the rented GPU (session 1, block A)

22 November 2026, 04:25 to 04:55 UTC. vast.ai instance 61888788: RTX 5060 Ti 16 GB, image
`nvcr.io/nvidia/isaac-lab:3.0.0` (Isaac Lab 3.0.0, Newton 1.6.1, mujoco-warp 3.12.0, rsl-rl 5.5.1).
The instance had been running since 01:23 UTC, so 3.5 GPU hours were used before any training.

## Model

Scorbi v0.5, commit `41fbd3d` (1,253 g). The owner decided: train on v0.5, and use the model's own
torque limit of 1.18 N m for the motor check, not the build pack's 15 kg cm.

`training/tools/derive_training_model.py` writes the training MJCF from `scorpion/scorpion.xml`
(base at z = 0, actuators and keyframe removed, gains moved to the config). Isaac Lab's
`convert_mjcf.py` turns it into USD. The four foot bodies survive the import.

## Decision: Newton MuJoCo-Warp is the training backend

Evidence, from `training/tools/oracle.py` (158 checks, 0 problems, 16 robots, zero action):

| | Isaac Lab, Newton MJWarp, dt 0.005 | MuJoCo 4.0.1, `scene.xml`, dt 0.002 |
|---|---|---|
| Base height after 5 s | 71.674 mm | 71.67 mm |
| Tilt | 0.056° | 0.064° |
| Foot loads, fl fr rl rr | 3.362, 3.360, 2.789, 2.780 N | 3.362, 3.360, 2.789, 2.780 N |
| Busiest motor, standing | 8.8% of the limit | 8.0% |
| After a 5 cm drop | same height and loads; peak 37% of the limit | same height and loads |

The oracle also checks, joint by joint and by name: both limits, the standing pose, stiffness 9.0,
damping 0.17, armature 0.002, friction 0.02, torque limit 1.18 and speed limit 9.6; the mass; that
each foot and the base report contact; that the action drives the 12 leg joints in the model's
order; and that the control step is 0.02 s. Isaac Lab's joint order here equals the model's order.

Not yet checked: motion. The scripted gait in both simulators is block B.

## Throughput

20 iterations, 4,096 robots, 24 steps each: 164,000 steps a second, 0.60 s an iteration. So a
500-iteration probe is 5 minutes and 15,000 iterations is 2.5 hours. Isaac Lab's stock Go2 flat task
on the same GPU: 0.67 s an iteration.

## Anomalies

1. **The arm had no target.** The action term drives only the legs, and joints without a target are
   driven to zero. The elbow ran from -1.80 to its stop at 0 with the motor saturated. Fixed in
   `scorbi_lab/actions.py`: the same term holds the arm at a scripted target every step. The oracle
   now fails if any joint is more than 0.1 rad from the stand.
2. **Without reset events the robot is never put in its initial state.** It starts with every joint
   at zero (the knee is then outside its range) and the base in the floor, and the simulation
   reaches NaN in six control steps. The oracle's first version removed the reset events; it now
   keeps them with no scatter.
3. **Isaac Lab's zero-action agent exits 0 on a simulation that is all NaN.** A smoke test that
   only checks the exit code proves nothing. Check: the oracle asserts finite heights and joint
   errors.
4. **Contact capacity.** With the arm running into its stop, MJWarp reported `nefc overflow`
   (njmax 100 asked for up to 286) and `nconmax` 40 asked for 64. With the arm held there is no
   overflow in the oracle or in the 20-iteration run. Watch for these lines once robots fall.
5. **A random policy almost never falls.** In the 20-iteration run, 0.05% of episodes ended by body
   contact and 0.5% by tipping past 60°. Scorbi stands low and wide, and the action scale is 0.25 rad.
   "Try 1" will be a robot that shakes on the spot, not one that collapses. The accounts' fail
   labels will lean to `statue`, `jackhammer` and `worm` unless shoves or wider actions are added.
