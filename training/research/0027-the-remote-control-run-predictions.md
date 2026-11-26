# 0027 · The remote-control run: predictions

26 November 2026, 13:38 UTC. Written before the run starts. Instance 62662296.

## What the probe showed at iteration 1,000

`remote_probe_s1` (0026) is still training. An early look at iteration 1,000 (8 seeds, batch `peek`):

- Slow commands pass again: forward 0.06 m/s on 7 of 8 (`all_fast_s1` at 1,500: 11 of 32), forward 0.12,
  sideways 0.08 and the shoved walk on 8 of 8.
- Every faster command passes on 8 of 8: forward 0.366 m/s, backward 0.307, sideways 0.214 both ways, turn
  1.99 and 2.01 rad/s, the fast curve and the fast diagonal.
- No leg joint goes over 9.6 rad/s on any of them; the largest is 9.4 rad/s on the fast curve
  (`all_fast_s1`: over the limit up to 16% of the time).

`production_fast_limit_a` (0025) at iteration 3,000, also an early look: 0.360 m/s told 0.36, 8 of 8, largest
leg joint speed 7.6 rad/s, largest torque 1.07 N·m. Both changes do what they were made for, so the long run
starts now and does not wait for the probe's last checkpoint.

## The run

`remote_a`: task `Scorbi-Velocity-Flat-Remote`, seed 1, 6,000 iterations, beside `production_fast_limit_a`.

Against `production_fast_limit_a`, the commands change: forward and backward to 0.40 m/s (0.9 mph), sideways
to 0.30 m/s (0.67 mph), turning to 2.5 rad/s, and 40% of the robots draw from ranges 0.3 times as wide. Same
reward (rung 2 with `leg_speed_over`), same eight disturbance groups.

It is evaluated on 23 commands. The shove ladder and the ball hit the slow walk, the stand and the 0.8 mph walk.

## Predictions for iteration 6,000

| Prediction | How sure |
|---|---|
| Passes all 32 seeds of each of the 13 usual commands. | 60% |
| Passes every one of the ten faster commands on 28 or more of 32. | 55% |
| No command has a leg joint over 9.6 rad/s for more than 2% of the time. | 65% |
| Reaches 0.33 m/s or more told 0.36 forward, and 0.28 m/s or more told 0.31 backward. | 55% |
| Reaches 0.20 m/s or more sideways both ways told 0.22. | 50% |
| The first checkpoint that passes every command comes later than `production_fast_a`'s (1,500). | 70% |

Wrong would be: with the disturbances on, the fast sideways walk or the fast turn cannot be had inside the
servo's speed, and it gives up one direction (as `all_fast_s1` gave up the slow walk).

## Not decided by this run

Whether a remote control should reach these speeds at all on the real robot. Every number is from simulation
on flat ground.
