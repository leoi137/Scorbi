# 0020 · How fast can it walk? Two probes on a new instance

26 November 2026, 08:30 UTC. Written before the runs start.

## Why

The owner watched the walk and found it far too slow. Every run of session 1 was told to walk forward at
0.15 m/s at most (0.34 mph), because the website asks for 0.12 m/s (0.27 mph); the clips show that speed and
the robot tracks it. No run was ever asked for more, so how fast Scorbi can walk is not known. The owner asked
for a try at 0.7 to 0.8 mph (0.31 to 0.36 m/s).

A calculation, not a measurement: the production walk takes 3.9 steps a second of 31 mm each. The legs (thigh
60 mm, shin 99 mm) allow strides of about 80 mm, which at the same step rate is 0.31 m/s. The servos' speed
limit of 9.6 rad/s caps the swing of a foot near 1 m/s, which puts the ceiling near 0.45 m/s (1 mph).

## The instance

The owner deleted instance 61888788 and rented 62662296 (RTX 5060 Ti, the same Isaac Lab 3.0.0 image, $0.134
an hour). Everything on the old disk is gone, including the converted training model; the copies of every run
are on the orb and in Drive (0016). The model is derived again from Scorbi commit `41fbd3d` with the same
scripts, and the oracle is run again before any training.

## The two runs

Rung 2 (tracking, action rate, fell, leg torque), no disturbances, seed 1, 1,500 iterations each, at the same
time. One thing changes against `ladder2_s1`: the forward command goes up to 0.40 m/s (0.9 mph).

| Run | Task | Tracking width |
|---|---|---|
| `fast_s1` | `Scorbi-Velocity-Flat-Fast` | 0.15 m/s |
| `fast_narrow_s1` | `Scorbi-Velocity-Flat-Fast-Narrow` | 0.075 m/s, as every run so far |

- The width has to be chosen again. The plan's rule (half the top command) gives 0.20 m/s; a reward about that
  wide let `stock_reward_s1` fail the stand command on every seed (0007). At 0.075 a robot walking at 0.12 m/s
  when told 0.36 is paid nothing and has no slope to climb, except through the commands in between.
- Both are evaluated on the usual 13 commands and two more: forward at 0.31 m/s (`forward_07mph`) and at
  0.36 m/s (`forward_08mph`), 32 seeds each, with the usual test (no fall, 70% of the commanded speed).

| Prediction | How sure |
|---|---|
| `fast_s1` passes `forward_07mph` on 24 or more of 32 seeds at iteration 1,500. | 55% |
| `fast_s1` reaches a mean of 0.30 m/s or more when told 0.36 m/s. | 40% |
| At 0.36 m/s more than half of `fast_s1`'s episodes are red on the motor check (a joint at its torque limit over 5% of the time). | 50% |
| `fast_s1` falls in fewer than 4 of 32 episodes at 0.36 m/s. | 60% |
| `fast_narrow_s1` is slower than `fast_s1` when told 0.36 m/s, by 0.05 m/s or more. | 55% |
| `fast_s1` still passes all 32 seeds of the stand command. | 65% |
