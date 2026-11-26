# 0034 · Past 0.9 mph: what the network already does, and one run (predictions)

26 November 2026, 16:26 UTC. Instance 62662296.

## A correction to 0032

0032 said `production_fast_limit_a` was trained to 0.36 m/s and that 0.40 m/s was outside its training. Wrong:
its forward commands go to 0.40 m/s (`FAST_FORWARD` in `fast.py`). 0.36 m/s is the fastest command the usual
evaluation tests. 0033 has the right version. (An earlier version of this note said I had told the owner the
wrong one. I had not; it was only in 0032 and in my log.)

## Told to go faster than it was trained (`production_fast_limit_a`, iteration 6,000, batch `sweep_top`)

| Told | Reached | Passed | Largest leg joint speed (servo 9.6 rad/s) | Torque, largest and 99th percentile (limit 1.18 N·m) | Motor check (green / amber / red) |
|---|---|---|---|---|---|
| 0.45 m/s (1.0 mph) | 0.449 m/s | 32 of 32 | 8.7 rad/s | 1.13 and 0.92 N·m | 17 / 15 / 0 |
| 0.50 m/s (1.1 mph) | 0.492 m/s | 32 of 32 | 8.6 rad/s | 1.18 and 1.03 N·m | 17 / 15 / 0 |
| 0.54 m/s (1.2 mph) | 0.525 m/s | 32 of 32 | 8.8 rad/s | 1.18 and 1.12 N·m | 0 / 32 / 0 |

No falls. Travel per touchdown grows from 77 mm at 0.36 m/s to 99, 104 and 108 mm; touchdowns a second stay at
4.6 to 4.9 per foot. Joint speed, torque and step from the 4 seeds with full detail, after the first 5 s.

So the network that was paid to keep its legs under the servo's speed walks 1.0 mph inside both the speed and
the torque limit, without ever having been told to, and reaches the torque limit from 1.1 mph. `top_speed_s1`
(0026), trained to 0.55 m/s without that price, needed 10.5 rad/s for 1.0 mph. 0026's "honest top is 0.8 to
1.0 mph" was too low for this network: here it is 1.0 to 1.1 mph. Not tested at these speeds: shoves, the
ball, and whether weak motors (a disturbance in training) leave room.

## The run

`production_top_limit_a`: task `Scorbi-Velocity-Flat-Production-Top-Limit`, seed 1, 6,000 iterations, alone on
the GPU. The one change against `production_fast_limit_a`: forward commands up to 0.50 m/s for 0.40. The
evaluation then also tests `forward_10mph` (0.45 m/s). No training-noise batch: the instance ends at 19:00 UTC
and the copy has to be out by then.

| Prediction for iteration 6,000 | How sure |
|---|---|
| Passes `forward_10mph` on 28 or more of 32. | 85% |
| Reaches 0.43 m/s or more told 0.45. | 80% |
| At 0.45 m/s no leg joint is over 9.6 rad/s for more than 2% of the time. | 75% |
| Passes all 32 seeds of each of the 13 usual commands. | 75% |
| Still reaches 0.35 m/s or more told 0.36. | 85% |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up. | 70% |

I am giving these higher than my habit today (0033: 22 of 26 held at 50% to 70%).

Wrong would be: trained on commands up to 0.50 m/s it spends the torque it has on the top speed, and the slow
walk, the stand or the shoves get worse than `production_fast_limit_a`'s.
