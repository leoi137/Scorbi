# 0030 · The 0.8 mph walk, inside the servo's speed

26 November 2026, 15:16 UTC. Results of `production_fast_limit_a` (predicted in 0025). Instance 62662296.
Its training-noise batch (iterations 0 to 800) is still running; its result goes into the next note.

## `production_fast_limit_a`, iteration 6,000: 16 commands, 32 seeds each

512 of 512 pass, no falls, gait trot. Checkpoint hash `53536708c8eada22`.
Against `production_fast_a` the only change is the reward term `leg_speed_over` (-1.0, above 8.64 rad/s).

| | `production_fast_limit_a` | `production_fast_a` (0024) |
|---|---|---|
| Speed told 0.36 m/s (0.8 mph) | 0.362 m/s, 32 of 32 | 0.353 m/s, 32 of 32 |
| Speed told 0.31 m/s (0.7 mph) | 0.311 m/s | 0.305 m/s |
| Largest leg joint speed at 0.36 m/s (servo: 9.6 rad/s) | 7.8 rad/s | 13.1 rad/s |
| Time with some leg joint over 9.6 rad/s at 0.36 m/s | 0% | 22.3% |
| Largest torque at 0.36 m/s (limit 1.18 N·m) | 1.07 N·m | at the limit at times (all amber) |
| Motor check at 0.36 m/s (green / amber / red) | 25 / 7 / 0 | 0 / 32 / 0 |
| Travel per touchdown at 0.36 m/s | 77 mm, 4.70 touchdowns a second per foot | 75 mm |
| Falls in training (about 590,000 episodes) | 20 | 1,134 |
| First checkpoint that passes every command | 825 | 1,500 |
| Training time | 111 minutes (other runs shared the GPU) | 71 minutes |

- Joint speed and travel per touchdown are from the 4 seeds with full detail, after the first 5 s
  (`joint_speed.py`, `gait_facts.py`). An early look at 6,000 with 8 seeds (batch `peek`) gave 7.7 rad/s.
- The other 13 commands pass on all 32 seeds, mostly green (28 to 31 green of 32).
- After 825 it drops to 480 of 512 at 850, 875 and 900, and is 512 at 975, 1,200 and 1,500. Walking starts
  between 525 and 750.
- The walk did not get shorter steps to stay inside the servo: the same 77 mm per touchdown, with slower hips.
  I have not looked at where the speed comes from instead (the knee, or the timing).

## Shoved and hit while walking (iteration 6,000, episodes that stay up, of 32)

| | Shove 0.5 m/s | 1.0 m/s | 1.5 m/s | 2.0 m/s | Ball 3 m/s | 4 m/s | 5 m/s | 6 m/s |
|---|---|---|---|---|---|---|---|---|
| forward 0.36 m/s | 32 | 32 | 18 | 9 | 32 | 32 | 20 | 15 |
| forward 0.08 m/s | 32 | 32 | 25 | 8 | 32 | 25 | 21 | 9 |
| stand | 32 | 32 | 30 | 14 | 32 | 26 | 10 | 10 |
| `production_fast_a`, forward 0.36 m/s | 32 | 32 | 21 | 14 | 30 | 22 | 20 | 19 |

Against the big shoves at 0.8 mph it is weaker than `production_fast_a` (18 against 21 at 1.5 m/s, 9 against
14 at 2.0 m/s), and better against the ball at 3 and 4 m/s. One seed each, so the differences of 3 to 5
episodes in 32 are not settled. A leg that may not turn faster than the servo has less to catch a shove with;
that is a guess, not measured.

## Predictions of 0025

| Prediction for iteration 6,000 | How sure | Result |
|---|---|---|
| At 0.36 m/s some leg joint is over 9.6 rad/s for under 2% of the time. | 70% | Held: 0%. |
| It passes `forward_08mph` on 24 or more of 32 seeds. | 60% | Held: 32. |
| Mean speed of 0.33 m/s or more when told 0.36 m/s. | 50% | Held: 0.362. |
| It passes all 32 seeds of each of the 13 usual commands. | 70% | Held. |
| Travel per touchdown at 0.36 m/s is under 65 mm. | 60% | Wrong: 77 mm. |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up. | 55% | Held: 32. |

The "wrong would be" of 0025 (0.36 m/s cannot be had inside the servo's speed with the disturbances on) did
not happen. The videos can say 0.8 mph.

## What this does not show

- The simulator still does not hold a joint to 9.6 rad/s. The walk stays under it because it is paid to; a
  shove or a fall can still spin a joint faster than the servo could, and those moments are not checked.
- One seed of the production run. Flat ground. No real robot.

## Clips (in the run's `previews/`)

`iter6000_forward_08mph_seed0_pet.mp4`, `iter6000_forward_08mph_shoved_150_seed2_side.mp4` (tilts 53° and
walks on), `iter6000_forward_08mph_shoved_200_seed2_side.mp4` (falls), `iter6000_forward_08mph_ball_500_seed11_side.mp4`,
`iter6000_forward_08mph_ball_600_seed9_side.mp4` (falls). Frame sheets of the `shoved_150` and `ball_600` clips were looked at.
