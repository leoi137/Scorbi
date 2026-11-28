# 0026 · The probes go fast in every direction, and one forgets the slow walk

26 November 2026, 13:16 UTC. Results of the two probes of 0023, and the predictions for one more probe.
Instance 62662296.

## `top_speed_s1`, iteration 1,500 (forward commands up to 0.55 m/s)

576 of 576 pass (18 commands, 32 seeds), no falls. Checkpoint hash `d01f55d739cacb95`.

| Told | Reached | Motor check (green / amber / red) | Largest leg joint speed | Time with a leg joint over 9.6 rad/s |
|---|---|---|---|---|
| 0.36 m/s (0.8 mph) | 0.358 m/s | 32 / 0 / 0 | 9.4 rad/s | 0% |
| 0.45 m/s (1.0 mph) | 0.448 m/s | 23 / 9 / 0 | 10.5 rad/s | 3.6% |
| 0.54 m/s (1.2 mph) | 0.538 m/s | 0 / 32 / 0 | 11.6 rad/s | 9.0% |

- In the simulator it walks 1.2 mph. Inside the servo's speed limit the top is between 0.36 and 0.45 m/s
  (0.8 to 1.0 mph): the simulator does not hold a joint to that limit (0024).
- During training the slow forward command came and went: 0 of 32 at five checkpoints between 1,000 and
  1,300, 32 of 32 from 1,350 on.

## `all_fast_s1`, iteration 1,500 (every direction faster)

689 of 736 pass (23 commands), no falls. Checkpoint hash `32471a767e616f78`.

| Command | Reached | Passed | Time with a leg joint over 9.6 rad/s |
|---|---|---|---|
| backward 0.31 m/s (0.7 mph) | 0.314 m/s | 32 | 0% |
| sideways left / right 0.22 m/s (0.5 mph) | 0.224 / 0.224 m/s | 32 / 32 | 0.8% / 0% |
| turn left / right 2.0 rad/s (115°/s) | 2.01 / 2.00 rad/s | 32 / 32 | 3.5% / 11.5% |
| forward 0.31 m/s with turn 1.5 rad/s | 0.310 m/s, 1.52 rad/s | 32 | 4.6% |
| forward 0.25 m/s with sideways 0.15 m/s | 0.253, 0.152 m/s | 32 | 16.4% |
| forward 0.36 m/s | 0.366 m/s | 32 | 11.5% |
| **forward 0.06 m/s** | 0.020 m/s | **11** | 0% |
| forward 0.12 m/s | 0.109 m/s | 29 | |
| forward 0.08 m/s, shoved | 0.051 m/s | 21 | |
| sideways 0.08 m/s left / right | 0.073 / 0.069 m/s | 29 / 29 | |

- Every fast command passes. The slow ones do not: told 0.06 m/s it stands still on two episodes of three
  (label `statue`), and this did not get better over the last 22 checkpoints (11 to 23 of 32).
- With ranges this wide, few sampled commands are slow, and standing still at 0.06 m/s still earns half the
  tracking pay. `fast_narrow_s1` (forward range only) passed the slow command on 32 of 32.
- A remote control needs the slow end as much as the fast one.

## Predictions of 0023

| Prediction | How sure | Result |
|---|---|---|
| `top_speed_s1` passes `forward_10mph` on 24 or more of 32. | 45% | Held: 32. |
| `top_speed_s1` reaches 0.45 m/s or more when told 0.54. | 25% | Held: 0.538 m/s. |
| At 0.54 m/s more than half the episodes are red on the motor check. | 60% | Wrong: none red. |
| `top_speed_s1` still passes `forward_08mph` on all 32. | 70% | Held. |
| `all_fast_s1` passes `backward_07mph` on 24 or more. | 60% | Held: 32. |
| `all_fast_s1` passes both sideways commands at 0.22 m/s on 24 or more. | 50% | Held: 32 and 32. |
| `all_fast_s1` passes both turn commands at 2.0 rad/s on 24 or more. | 65% | Held: 32 and 32. |
| `all_fast_s1` passes all 32 seeds of each of the 13 usual commands. | 55% | Wrong: six of them fail seeds, forward slow 21 of 32. |

The motor check was the wrong instrument twice now: it counts time at the torque limit, and the limit these
walks break is the speed limit. 0020's ceiling calculation (0.45 m/s from the servo's speed) was about right
for a walk the servo can do, and wrong about what the simulator allows.

## One more probe before the remote-control run

`remote_probe_s1`: task `Scorbi-Velocity-Flat-Remote-Probe`, seed 1, 1,500 iterations, no disturbances. Two
changes against `all_fast_s1`, because the long run needs both and the day has room for one probe:

- **Slow commands stay common.** 40% of the robots draw their whole command from ranges 0.3 times as wide
  (forward and backward to 0.12 m/s, sideways to 0.09 m/s, turn to 0.75 rad/s). New in the sampler:
  `rel_slow_envs`, `slow_scale`. Off by default, and then the sampler draws the same numbers as before.
- **`leg_speed_over`** at -1.0, as in 0025.

| Prediction for iteration 1,500 | How sure |
|---|---|
| Passes `forward_slow` on 28 or more of 32 (`all_fast_s1`: 11). | 65% |
| Passes all 32 seeds of each of the 13 usual commands. | 45% |
| Passes every one of the ten faster commands on 24 or more of 32. | 55% |
| No command has a leg joint over 9.6 rad/s for more than 2% of the time (`all_fast_s1`: up to 16.4%). | 55% |
| Turning at 2.0 rad/s is the command that gives way: under 1.8 rad/s reached on one side. | 40% |

If it passes, the long run is `Scorbi-Velocity-Flat-Remote`: the same with the eight disturbance groups.

## Copy-out without the orb's disk

The orb has 2 GB free and the owner has not said the old copies may go. `drive_sync.py stream` sends a file
from the GPU into Drive through the orb's memory: the Drive token stays on the orb and the file never lands on
its disk. Only the JSON and log files are kept on the orb (they are what `rows.py` reads). Checked on a small
run: the SHA-256 recorded for a streamed file equals the GPU's own. The line from the GPU carries about
4.5 MB/s in all, so three files at a time.
