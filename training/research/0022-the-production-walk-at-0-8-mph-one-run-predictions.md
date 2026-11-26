# 0022 · The production walk at 0.8 mph: one run, predictions

26 November 2026, 10:45 UTC. Written before the run starts. Instance 62662296.

## Why

The owner saw the 0.8 mph walk of 0021 and wants the walk that goes on the website and into the videos to be
that fast. The two probes of 0021 had no disturbances and 1,500 iterations. The website candidate
(`production_plain_a`, 0015) had all eight disturbance groups and 6,000 iterations, and was told 0.15 m/s at most.

## The run

`production_fast_a`: task `Scorbi-Velocity-Flat-Production-Fast`, seed 1, 6,000 iterations.

- One change against `production_plain_a`: the forward command range goes from -0.12 to 0.15 m/s to -0.12 to
  0.40 m/s. Same reward (rung 2, tracking width 0.075 m/s), same eight disturbance groups at the same sizes.
- One seed, not two: this orb has 16 GB of disk left and the copies of request 13 are still coming in.
- After training: the usual batches, then the training-noise batch for iterations 0 to 500 (as request 13).

## A shoved command at 0.8 mph

The evaluation gets a 16th command for runs trained to walk fast: `forward_08mph_shoved` (0.36 m/s). It is
shoved at 0.10 m/s in the fixed-seed batch like the other two shoved commands, and the shove ladder (0.5 to
2 m/s) and the ball (3 to 6 m/s) now hit it too. It comes last, so the other 15 keep their places.

Tried first on `fast_narrow_s1` iteration 1,500, 16 seeds (batch `peek`): 16 of 16 pass at the 0.10 m/s shove,
0.357 m/s, all green. That run never saw a shove in training.

## Predictions for iteration 6,000

| Prediction | How sure |
|---|---|
| Passes `forward_08mph` on 24 or more of 32 seeds. | 70% |
| Mean speed of 0.33 m/s or more when told 0.36 m/s. | 60% |
| Passes all 32 seeds of each of the 13 usual commands. | 75% |
| At 0.36 m/s more than half of the episodes are amber or red on the motor check (`fast_narrow_s1`: 1 of 32). | 60% |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up. | 50% |
| The first checkpoint that passes every command comes later than `production_plain_a`'s (iteration 375). | 65% |

Wrong would be: it parks or shuffles at the fast commands because a robot with motors drawn 20% weak cannot
make 0.36 m/s, and the policy learns one cautious walk for all of them.

## Not decided by this run

Whether it replaces `production_plain_a` on the website: that needs the website's own check (0012, 0015), which
does not use the GPU. Sideways (0.10 m/s), backward (0.12 m/s) and turning (1.2 rad/s) keep their old ranges.
