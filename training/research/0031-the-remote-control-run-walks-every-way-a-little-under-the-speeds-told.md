# 0031 · The remote-control run walks every way, a little under the speeds it is told

26 November 2026, 15:47 UTC. Results of `remote_a` (predicted in 0027), and the training-noise batch of
`production_fast_limit_a` (0030). Instance 62662296. `remote_a`'s own training-noise batch (0029) is running.

## `remote_a`, iteration 6,000: 23 commands, 32 seeds each

672 of 736 pass, no falls, gait trot. Checkpoint hash `998944bf6cfde6be`.
Training: 589,859 episodes, 94 falls, 99 minutes. All eight disturbance groups on.

| Command | Told | Reached | Passed | Largest leg joint speed (limit 9.6 rad/s) | Motor check (green / amber / red) |
|---|---|---|---|---|---|
| stand | 0 | 0.000 m/s | 0 | 0 | 15 / 17 / 0 |
| forward slow | 0.06 m/s | 0.052 m/s | 32 | 5.6 rad/s | 5 / 27 / 0 |
| forward 0.8 mph | 0.36 m/s | 0.340 m/s (0.76 mph) | 32 | 9.1 rad/s | 0 / 32 / 0 |
| forward 0.7 mph | 0.31 m/s | 0.313 m/s | 32 | | 0 / 32 / 0 |
| backward 0.7 mph | 0.31 m/s | 0.299 m/s | 32 | 8.7 rad/s | 0 / 32 / 0 |
| sideways left / right 0.5 mph | 0.22 m/s | 0.211 / 0.243 m/s | 32 / 32 | 8.9 / 7.8 rad/s | 10 / 22 / 0 and 8 / 24 / 0 |
| turn left / right | 2.0 rad/s (115°/s) | 1.85 / 1.67 rad/s (106 / 96°/s) | 32 / 32 | 9.2 / 8.7 rad/s | 0 / 32 / 0 |
| forward with a turn | 0.31 m/s, 1.5 rad/s | 0.278 m/s, 1.31 rad/s | 32 | 9.9 rad/s, over the limit 2.8% of the time | 0 / 32 / 0 |
| diagonal | 0.25 m/s, 0.15 m/s | 0.240 m/s, 0.161 m/s | 32 | 8.9 rad/s | 0 / 0 / 32 |

- The eleven slow moving commands pass on all 32 seeds.
- **`stand` and `stand_shoved` fail on all 32, by 0.1 mm.** The robot stands still (drift about 12 mm in 20 s,
  no joint moving). The test wants the body at 85% of `STAND_HEIGHT` or more: 0.0609 m. It stands at 0.0608 m;
  `production_fast_limit_a` stands at 0.0629 m. The label `wander` is the labeller's catch-all for a failed
  stand, not what happens. Five checkpoints pass all 736: 3,600, 5,400, 5,500, 5,600 and 5,800 (stand at
  0.0610 to 0.0612 m). The run sits on the test's line.
- **Checkpoint 5,800 passes every command** and is the same walker: forward 0.348 m/s told 0.36, backward
  0.300, sideways 0.207 / 0.226, turn 1.89 / 1.70 rad/s. It has no full-detail recording (only the last
  checkpoint has), so its joint speeds are not checked.
- **The fast diagonal is red on the motor check on all 32** (at 6,000 and at 5,800): a leg joint within 2% of
  the torque limit for over 5% of the time upright. It was green on the probe (0028), which had no weak motors.
- Joint speeds are from the 4 seeds a command with full detail, after the first 5 s.
- Learning is late: 0 of 736 at iteration 800, walking from about 1,200, 640 at 3,000.

Against the probe without disturbances (0028: 736 of 736, speeds reached within 6%, turns 2.00 and 2.03):
with weak motors, delay, pushes and the rest, the same commands are reached up to 16% short (sideways right goes 10% over), most motor marks
are amber or red at the fast commands, and one command goes over the servo's speed a little.

## Shoved and hit (iteration 6,000, episodes that stay up, of 32)

| | Shove 0.5 m/s | 1.0 m/s | 1.5 m/s | 2.0 m/s | Ball 3 m/s | 4 m/s | 5 m/s | 6 m/s |
|---|---|---|---|---|---|---|---|---|
| forward 0.36 m/s told | 32 | 27 | 23 | 14 | 31 | 15 | 14 | 17 |
| forward 0.08 m/s | 32 | 32 | 26 | 13 | 32 | 20 | 13 | 6 |
| stand | 32 | 32 | 29 | 14 | 32 | 23 | 7 | 12 |
| `production_fast_limit_a`, forward 0.36 m/s (0030) | 32 | 32 | 18 | 9 | 32 | 32 | 20 | 15 |

At 0.8 mph it loses 5 of 32 to a 1.0 m/s shove, which `production_fast_limit_a` never does, and stands up to
the two biggest shoves more often. One seed each.

## Predictions of 0027

| Prediction for iteration 6,000 | How sure | Result |
|---|---|---|
| Passes all 32 seeds of each of the 13 usual commands. | 60% | Wrong: stand and stand shoved pass 0 (0.1 mm under the height line). |
| Passes every one of the ten faster commands on 28 or more of 32. | 55% | Held: 32 on each. |
| No command has a leg joint over 9.6 rad/s for more than 2% of the time. | 65% | Wrong, narrowly: the fast curve, 2.8% (largest 9.9 rad/s). The other eight checked: 0%. |
| Reaches 0.33 m/s or more told 0.36 forward, and 0.28 m/s or more told 0.31 backward. | 55% | Held: 0.340 and 0.299. |
| Reaches 0.20 m/s or more sideways both ways told 0.22. | 50% | Held: 0.211 and 0.243. |
| The first checkpoint that passes every command comes later than 1,500. | 70% | Held: 3,600. |

What 0027 called wrong (it gives up one direction) did not happen. What I did not predict: the stand sinking
2 mm, and the fast diagonal at the torque limit.

## `production_fast_limit_a`'s training-noise batch (iterations 0 to 800)

51 checkpoints, 26,112 episodes, no falls. Passes go from 2 of 512 at iteration 0 to 475 of 512 at 800. The
labels are `jackhammer`, `moonwalk` and `off_course` at the start, `treadmill` and `off_course` from about 90.
Seed 0 told 0.36 m/s moves at 0.01 to 0.02 m/s at iterations 0 to 675 and at 0.362 m/s at 800: again a jump
from not walking to walking, with no falling in between (0024 found the same).

## What this means for a remote control

- One network with the disturbances on walks every direction at 0.47 to 0.76 mph and turns at about 100°/s,
  inside the servo's speed except on the fast curve. That is the result to build on.
- Not ready as it is: the stand height, the fast diagonal at the torque limit, and turning 7% and 16% short.
  Lower top speeds for the diagonal (or a torque price that bites sooner) and a stand-height term are the two
  changes I would try first. Neither is run.
- Nothing between the slow and fast commands is tested, and it is one seed.
