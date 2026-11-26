# 0023 · Two probes: top speed, and every direction faster

26 November 2026, 11:00 UTC. Written before the runs start. Instance 62662296.

## Why

The owner approved a 9-hour plan (until 19:00 UTC) and will give users a remote control. Two things are not
known: where the forward speed stops (0021 reached 0.36 m/s with the legs touching their torque limit), and how
fast Scorbi can walk backward, sideways and turn. Every run so far was told at most 0.12 m/s backward, 0.10 m/s
sideways and 1.2 rad/s.

## The two runs

Both: rung 2 reward, tracking width 0.075 m/s, no disturbances, seed 1, 1,500 iterations, at the same time,
after `production_fast_a` (0022) finishes. One thing changes against `fast_narrow_s1`: the command ranges.

| Run | Task | Forward | Sideways | Turn |
|---|---|---|---|---|
| `top_speed_s1` | `Scorbi-Velocity-Flat-TopSpeed` | -0.12 to 0.55 m/s (1.2 mph) | ±0.10 m/s | ±1.2 rad/s |
| `all_fast_s1` | `Scorbi-Velocity-Flat-AllFast` | -0.40 to 0.40 m/s (0.9 mph both ways) | ±0.30 m/s (0.67 mph) | ±2.5 rad/s (143°/s) |

`all_fast_s1` changes three ranges at once. If it fails a direction, a second probe has to separate them.

## New test commands

A run is rolled out on every extra command that lies inside the ranges it trained on. They come after the 13
and after the three of 0020 and 0022, 32 seeds each, the usual test (no fall, 70% of the commanded speed).

| Command | Value | For |
|---|---|---|
| `forward_10mph`, `forward_12mph` | 0.45 and 0.54 m/s | `top_speed_s1` |
| `backward_07mph` | -0.31 m/s | `all_fast_s1` |
| `sideways_left_05mph`, `sideways_right_05mph` | ±0.22 m/s | `all_fast_s1` |
| `turn_left_fast`, `turn_right_fast` | ±2.0 rad/s (115°/s) | `all_fast_s1` |
| `curve_left_fast` | 0.31 m/s forward with 1.5 rad/s | `all_fast_s1` |
| `diagonal_fast` | 0.25 m/s forward with 0.15 m/s sideways | `all_fast_s1` |

## Predictions for iteration 1,500

| Prediction | How sure |
|---|---|
| `top_speed_s1` passes `forward_10mph` (0.45 m/s) on 24 or more of 32 seeds. | 45% |
| `top_speed_s1` reaches a mean of 0.45 m/s or more when told 0.54 m/s. | 25% |
| `top_speed_s1` at 0.54 m/s: more than half of the episodes are red on the motor check. | 60% |
| `top_speed_s1` still passes `forward_08mph` on all 32 seeds. | 70% |
| `all_fast_s1` passes `backward_07mph` on 24 or more of 32 seeds. | 60% |
| `all_fast_s1` passes both sideways commands at 0.22 m/s on 24 or more of 32 seeds. | 50% |
| `all_fast_s1` passes both turn commands at 2.0 rad/s on 24 or more of 32 seeds. | 65% |
| `all_fast_s1` passes all 32 seeds of each of the 13 usual commands. | 55% |

The ceiling calculation of 0020 (servo speed 9.6 rad/s caps the walk near 0.45 m/s) is what `top_speed_s1`
tests. Wrong would be: it walks 0.54 m/s with the motor check green.

## What follows

The remote-control production run takes, for each direction, the fastest command that passes here on all 32
seeds without a red motor mark, with the eight disturbance groups, for 6,000 iterations.
