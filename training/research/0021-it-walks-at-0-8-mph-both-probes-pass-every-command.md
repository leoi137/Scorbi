# 0021 · It walks at 0.8 mph: both probes pass every command

26 November 2026, 10:00 UTC. Results of the two runs predicted in 0020. Instance 62662296.

## Final checkpoint (iteration 1,500), 15 commands, 32 seeds each

| Run | Passed | Falls | Told 0.31 m/s (0.7 mph) | Told 0.36 m/s (0.8 mph) | Motor check at 0.36 m/s | Largest tilt at 0.36 m/s |
|---|---|---|---|---|---|---|
| `fast_s1` (width 0.15) | 480 of 480 | 0 | 0.304 m/s | 0.355 m/s (0.79 mph) | 6 green, 26 amber, 0 red | 6.8° |
| `fast_narrow_s1` (width 0.075) | 480 of 480 | 0 | 0.308 m/s | 0.357 m/s (0.80 mph) | 31 green, 1 amber, 0 red | 7.0° |

- The 13 usual commands still pass on all 32 seeds in both runs, the stand command included (speed 0.000 m/s).
  Told 0.12 m/s they walk 0.117 and 0.118 m/s.
- Checkpoint hashes (SHA-256, first 16): `fast_s1` `5d5643272ae2d2ae`, `fast_narrow_s1` `35bb8c6fb74f47b7`.
- `fast_s1` at iteration 300 already did 0.353 m/s when told 0.36 (8 seeds, batch `peek`, 32 of 32 passed).

## How it goes faster

From the full-detail recordings (4 seeds a command, the last 15 s of each; a touchdown is a foot's vertical
force rising through 0.5 N, so contact chatter can inflate the step rate):

| Checkpoint | Command | Speed | Touchdowns a second, per foot | Travel per touchdown | Leg torque, largest / 99th percentile | Leg joint speed, largest / 99th percentile |
|---|---|---|---|---|---|---|
| `production_plain_a` 6000 | 0.12 m/s | 0.120 m/s | 4.0 | 30 mm | 0.90 / 0.65 N·m | 7.4 / 6.5 rad/s |
| `fast_narrow_s1` 1500 | 0.12 m/s | 0.121 m/s | 3.3 | 36 mm | 0.68 / 0.53 N·m | 4.7 / 4.2 rad/s |
| `fast_narrow_s1` 1500 | 0.31 m/s | 0.314 m/s | 5.0 | 63 mm | 1.18 / 0.85 N·m | 7.9 / 6.6 rad/s |
| `fast_narrow_s1` 1500 | 0.36 m/s | 0.365 m/s | 6.2 | 59 mm | 1.18 / 0.98 N·m | 8.7 / 7.4 rad/s |
| `fast_s1` 1500 | 0.36 m/s | 0.359 m/s | 7.6 | 47 mm | 1.18 / 1.04 N·m | 9.6 / 8.0 rad/s |

- Both longer and quicker steps: about twice the travel per step and one and a half times the step rate.
- At 0.36 m/s the legs touch the torque limit (1.18 N·m) at the peaks and come within 10% of the speed limit
  (9.6 rad/s). The motor check stays green or amber because the time spent at the limit is small: over the 32 seeds
  at most 0.1% of an episode in `fast_s1` and under 0.05% in `fast_narrow_s1`. There is little room above
  0.8 mph with these servos.
- The narrow run walks 0.36 m/s with fewer, longer steps than the wide run and with less strain.

## What was not tested

- Shoves and the ball were run only at the usual slow walk and at stand, as the standard batches do. Neither
  run saw a disturbance in training. At iteration 1,500: shoves 204 of 256 (`fast_s1`) and 201 of 256
  (`fast_narrow_s1`), all passing up to 1.0 m/s; the ball 156 and 155 of 256, all passing at 3 m/s. Nothing is
  known about a shove at 0.8 mph.
- One seed of training each. No friction, mass or motor variation. Flat ground.
- The noise batch (exploration noise 1.0 on the actions) fails at these speeds as it does at every speed: it is
  footage of exploring, not a test.

## Predictions of 0020

| Prediction | How sure | Result |
|---|---|---|
| `fast_s1` passes `forward_07mph` on 24 or more of 32 seeds. | 55% | Held: 32 of 32. |
| `fast_s1` reaches 0.30 m/s or more when told 0.36 m/s. | 40% | Held: 0.355 m/s. |
| More than half of `fast_s1`'s episodes at 0.36 m/s are red on the motor check. | 50% | Wrong: 0 red, 26 amber. |
| `fast_s1` falls in fewer than 4 of 32 episodes at 0.36 m/s. | 60% | Held: 0 falls. |
| `fast_narrow_s1` is slower than `fast_s1` at 0.36 m/s by 0.05 m/s or more. | 55% | Wrong: 0.357 against 0.355 m/s, and it strains the motors less. |
| `fast_s1` still passes all 32 seeds of the stand command. | 65% | Held. |

The session-1 speed of 0.12 m/s was the command, not a limit of the robot. The worry that a narrow tracking
reward gives no slope towards a fast command was wrong: the commands in between are enough.

## Clips

In `fast_narrow_s1/scorbi/previews/`, all of iteration 1,500, command 0.36 m/s, seed 0 (0.362 m/s, green):

- `iter1500_forward_08mph_seed0_side_wide.mp4`: side camera, 8 s.
- `iter1500_forward_08mph_seed0_race.mp4`: the new still camera `race` (side-on, `--hold 2.3` frames a 2.3 m path).
- `iter1500_forward_08mph_seed0_race_vs_production_plain_a_6000.mp4`: the same 6 s of `production_plain_a`
  iteration 6000 at 0.12 m/s above, this run below, same framing.

`render.py` gains `--hold` and the `race` camera. With the three-quarter `fixed` camera a long hold puts the
camera so far back that the scene's fog (it starts at 1.5 m) hides the robot; `race` stays near enough.

## Also on this instance

Queued behind the two probes: Account 1's request 13, the training-noise batches of the four production runs
(0018), about one GPU hour. It started at 09:50 UTC.
