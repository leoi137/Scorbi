# 0035 · Trained to 1.1 mph: a quick shuffle that takes shoves better

26 November 2026, 18:07 UTC. Results of `production_top_limit_a` (predicted in 0034). Instance 62662296.
This is the last run of the session. Nothing is running on the GPU.

## `production_top_limit_a`, iteration 6,000: 18 commands, 32 seeds each

576 of 576 pass, no falls, gait trot. Checkpoint hash `cb2edc8e0d234047`.
The one change against `production_fast_limit_a`: forward commands up to 0.50 m/s for 0.40.
Training: 589,887 episodes, 147 falls, 72 minutes alone on the GPU.

| | `production_top_limit_a` | `production_fast_limit_a` (0030, 0034) |
|---|---|---|
| Told 0.45 m/s (1.0 mph) | 0.448 m/s, 32 of 32 | 0.449 m/s, 32 of 32 (never trained on it) |
| Told 0.36 m/s (0.8 mph) | 0.354 m/s | 0.362 m/s |
| Largest leg joint speed at 0.45 m/s (servo 9.6 rad/s) | 7.9 rad/s | 8.7 rad/s |
| Torque at 0.45 m/s, largest and 99th percentile (limit 1.18 N·m) | 1.18 and 1.16 N·m | 1.13 and 0.92 N·m |
| Motor check at 0.45 m/s (green / amber / red) | 0 / 32 / 0 | 17 / 15 / 0 |
| Motor check at 0.36 m/s | 12 / 20 / 0 | 25 / 7 / 0 |
| Touchdowns a second per foot, and travel per touchdown, at 0.45 m/s | 7.9, 57 mm | 4.6, 99 mm |
| The same at 0.36 m/s | 7.5, 48 mm | 4.7, 77 mm |
| Falls in training | 147 | 20 |
| First checkpoint that passes every command | 1,100 (and all 49 read after it) | 825 |

- The 13 usual commands pass on all 32 seeds, with 7 to 22 of 32 green on the motor check and the rest amber.
- Joint speed, torque and steps are from the 4 seeds with full detail, after the first 5 s.
- **It is a different gait.** Told to reach 1.1 mph it did not lengthen the step of the 0.8 mph walk; it took
  short steps two thirds faster, at every speed, with the legs at the torque limit for much of the stride.

## Shoved and hit (iteration 6,000, episodes that stay up, of 32)

| | Shove 0.5 m/s | 1.0 m/s | 1.5 m/s | 2.0 m/s | Ball 3 m/s | 4 m/s | 5 m/s | 6 m/s |
|---|---|---|---|---|---|---|---|---|
| forward 0.45 m/s (1.0 mph) | 32 | 32 | 26 | 14 | 32 | 32 | 22 | 22 |
| forward 0.36 m/s (0.8 mph) | 32 | 32 | 26 | 15 | 32 | 29 | 26 | 23 |
| forward 0.08 m/s | 32 | 32 | 29 | 15 | 32 | 26 | 25 | 9 |
| stand | 32 | 32 | 29 | 14 | 32 | 27 | 8 | 8 |
| `production_fast_limit_a`, forward 0.36 m/s | 32 | 32 | 18 | 9 | 32 | 32 | 20 | 15 |
| `production_fast_a`, forward 0.36 m/s (over the servo's speed) | 32 | 32 | 21 | 14 | 30 | 22 | 20 | 19 |

At 0.8 mph the quick gait stays up more often than `production_fast_limit_a` at the two big shoves (26 and 15
against 18 and 9) and at the two fast balls (26 and 23 against 20 and 15), and less often at the 4 m/s ball
(29 against 32). At 1.0 mph it is as good as at 0.8 mph. One seed of each run: differences of 8 in 32 are
probably real, differences of 3 are not settled. Why short quick steps catch a shove better is not measured;
a foot is never far from its next touchdown, which is my guess.

## Predictions of 0034

| Prediction for iteration 6,000 | How sure | Result |
|---|---|---|
| Passes `forward_10mph` on 28 or more of 32. | 85% | Held: 32. |
| Reaches 0.43 m/s or more told 0.45. | 80% | Held: 0.448. |
| At 0.45 m/s no leg joint is over 9.6 rad/s for more than 2% of the time. | 75% | Held: 0%. |
| Passes all 32 seeds of each of the 13 usual commands. | 75% | Held. |
| Still reaches 0.35 m/s or more told 0.36. | 85% | Held: 0.354. |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up. | 70% | Held: 32. |
| Shoved at 1.0 m/s while walking at 0.45 m/s, 24 or more of 32 stay up. | 70% | Held: 32. |
| Shoved at 1.5 m/s while walking at 0.45 m/s, fewer than 18 of 32 stay up. | 55% | Wrong: 26. |

Seven of eight held. What 0034 called wrong (the top speed costs the slow walk, the stand or the shoves) did
not happen: the shoves got better. What I did not predict at all is the change of gait and its price, the
motors at the torque limit.

## Which walk for what

- **For the videos and for a first real robot, `production_fast_limit_a`** is still the walk I would show: a
  longer, slower step, mostly green on the motor check, and it does 0.1 to 1.0 mph already (0033, 0034). A
  servo held at its torque limit heats, and nothing in the simulator counts heat.
- **`production_top_limit_a` is the sturdier one in simulation**, and the only one trained and shoved at 1.0 mph.
  Whether its torque can be bought down (a higher price on torque) while keeping the quick step's balance is
  the next question. Not run.
- One seed each, flat ground, no real robot.

## Clips (in the run's `previews/`)

`iter6000_peek_forward_10mph_seed0_pet.mp4` and `_side.mp4`, `strip_10mph_vs_production_fast_limit_a_seed0_side.mp4`
(the two gaits at 1.0 mph, one above the other), `iter6000_forward_10mph_shoved_150_seed14_side.mp4`.
