# 0025 · A price on leg speed over the servo's: one run, predictions

26 November 2026, 12:32 UTC. Written before the run starts. Instance 62662296.

## Why

`production_fast_a` walks 0.36 m/s (0.8 mph) with its hip-lift joints over the servo's speed limit of 9.6 rad/s
for 22% of the time, up to 13.1 rad/s (0024). The simulator does not hold a joint to that limit. The probes
without disturbances walk the same speed inside it, so the speed can be had honestly.

## The term

`leg_speed_over` (ladder.py): for each of the twelve leg joints, how much faster than 8.64 rad/s (90% of the
servo's limit) it turns, squared and summed [rad²/s²]. Weight -1.0.

Priced on the recordings of 0024 (4 seeds a command, after the first 5 s), per second:

| Walk | Told 0.12 m/s | Told 0.31 m/s | Told 0.36 m/s |
|---|---|---|---|
| `production_fast_a` 6000 | 0.00 | 0.90 | 1.58 |
| `fast_narrow_s1` 1500 | 0.00 | 0.00 | 0.00 |
| `fast_s1` 1500 | 0.00 | 0.00 | 0.01 |

Tracking pays 1.5 a second at most. So the walk `production_fast_a` found does not pay at 0.8 mph, and a walk
inside the servo's speed costs nothing. This is steeper than the ladder's other prices (0.1 to 0.3 a second for
the baseline) on purpose: it stands in for a limit, not for a preference.

The term is also measured on every run from now on, rewarded or not (`ladder.measure`).

## The run

`production_fast_limit_a`: task `Scorbi-Velocity-Flat-Production-Fast-Limit`, seed 1, 6,000 iterations. One
change against `production_fast_a`: the reward gains `leg_speed_over`. It starts while the two probes of 0023
are still training, and the remote-control run will join it, so it runs slower than 71 minutes.

The weight is not probed first: the day has room for one long run of this, and every checkpoint is recorded
either way. Iteration 2,000's recording is read while it trains; if the joints are still over the limit as
much as in `production_fast_a`, the run is stopped and the weight raised.

## Predictions for iteration 6,000

| Prediction | How sure |
|---|---|
| At 0.36 m/s some leg joint is over 9.6 rad/s for under 2% of the time (`production_fast_a`: 22.3%). | 70% |
| It passes `forward_08mph` on 24 or more of 32 seeds. | 60% |
| Mean speed of 0.33 m/s or more when told 0.36 m/s. | 50% |
| It passes all 32 seeds of each of the 13 usual commands. | 70% |
| Travel per touchdown at 0.36 m/s is under 65 mm (`production_fast_a`: 75 mm; `fast_narrow_s1`: 59 mm). | 60% |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up (`production_fast_a`: 32). | 55% |

Wrong would be: with motors drawn 20% weak and a delay of up to two steps, 0.36 m/s cannot be had inside the
servo's speed, and it settles near 0.30 m/s at the fast commands. That would be the honest top speed of the
disturbed robot, and the videos would say 0.7 mph.
