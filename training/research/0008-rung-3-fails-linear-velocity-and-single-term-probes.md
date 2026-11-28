# 0008 · Rung 3 makes the walk worse, the policy stays blind, and rungs 4 to 6 are tried one at a time

22 November 2026, 07:50 UTC. GPU hours used so far: about 6.5. Written before `l2_drag_s1`, `l2_bounce_s1` and
`l2_fidget_s1` start. `ladder4_s1` (on top of rung 3) and `ladder1_steps_s1` are running.

## Rung 3 (`foot_slip`, weight -1.0) against 0005

`ladder3_s1`, final checkpoint, against rung 2:

| | Rung 2 | Rung 3 |
|---|---|---|
| Passed of 416 | 416 | 416 |
| Foot slip, forward 0.12 m/s | 0.10 m/s | 0.04 m/s |
| Share of time with three or more feet down | 0.35 | 0.07 |
| Share of time a diagonal pair is in the air | 0.66 | 0.93 |
| Highest mean motor torque, walking / standing | 0.17 / 0.24 N·m | 0.28 / 0.44 N·m |
| `body_bounce`, forward 0.12 m/s | 0.021 | 0.115 |
| `action_rate`, forward 0.12 m/s | 0.23 | 0.72 |
| Largest tilt on walking commands | 3.6° | 6.5° |
| Green / amber / red | 416 / 0 / 0 | 302 / 114 / 0 |

- **Predicted (60%): slip halves and nothing else moves much. The first half is right, the second is wrong.**
- The policy cut slip by keeping its feet off the floor: a foot in the air cannot slip. It stands and walks
  on two feet almost all the time, bounces five times as much, and its motors work harder. Told to stand, every
  episode is amber (0.44 N·m against the everyday rating of 0.36).
- **Decision: rung 3 is not kept.** The per-command test is unchanged and the look is worse (plan 5.4).
- `ladder4_s1` was already training on top of rung 3 and is left to finish, as a recorded probe.
  `ladder5_s1` and `ladder6_s1`, which would also sit on rung 3, are cancelled before starting
  (`/workspace/skip/`, a new switch in `run_recorded.sh`).
- Instead rungs 4, 5 and 6 are each added alone to rung 2: `l2_drag_s1`, `l2_bounce_s1`, `l2_fidget_s1`.

## The actor also sees its linear velocity, against 0003

`linvel_s1`: the tracking-only baseline with base linear velocity added to the policy's inputs (54 numbers).

- **Predicted (55%): tracks better, by less than 20%. Wrong: it does not track better.** Forward 0.117 m/s at
  0.12 (blind baseline 0.119), turn 0.99 rad/s (0.99). It passes 384 of 416 against 416: told to stand it
  creeps (`wander`, 32 of 32). All episodes red, like the blind baseline.
- **Decision: the policy stays blind** (plan 2.5). One seed each; the difference at stand may be seed noise.

## Check: do the randomised numbers reach the solver?

0007 listed this as not checked. Checked now, on all eight groups with 512 robots, by reading MuJoCo-Warp's own
per-world arrays after the first steps (they are still the nominal values before any step):

- foot friction: 4 of the model's friction columns differ between worlds, up to 1.30;
- torque limit (`jnt_actfrcrange`): differs on all 15 joints; it is limited on all 15, at ±1.18 N·m when not randomised;
- gains (`actuator_gainprm`, `actuator_biasprm`): differ on all 15 position and 15 velocity actuators;
- mass: the body and the claw's finger differ.

By effect: after the same 1 m/s shove, how far a standing robot slides correlates with its feet's friction at
-0.52 (lowest-friction fifth 43 mm, highest fifth 35 mm).

Standing needs little torque: 0.13 N·m at the model's mass, and 0.89 N·m with 8 kg added to the body. The
1.18 N·m limit was not reached in that test, so the limit was read, not exercised.

## Probes: rungs 4, 5 and 6, one at a time on rung 2

| Run | One change from rung 2 | Prediction | How sure |
|---|---|---|---|
| `l2_drag_s1` | + `foot_drag` (weight -0.3) | Swing lift rises from 8.7 mm to 11 mm or more. It may copy rung 3's trick (feet kept in the air): if the share of time with three or more feet down falls under 0.2, it is not kept. Slow forward does not park. | 45% that it lifts without the trick |
| `l2_bounce_s1` | + `body_bounce` (weight -2.0) | No visible change: rung 2 already bounces little (0.021, a cost of 0.04 a second). | 70% |
| `l2_fidget_s1` | + `fidget_at_rest` (weight -0.2) | No visible change when walking. Standing torque falls under rung 2's 0.24 N·m and stand drift stays under 10 mm. | 60% |

A term is kept only if the per-command test and the look both improve on rung 2. "No change" means it is left out.

`whatif_tall_s1` (0006's prediction stands: it stretches its legs and stands; it never walks) runs after them.
