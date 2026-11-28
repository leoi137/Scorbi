# 0024 · The production walk does 0.8 mph, but its hips turn faster than the servo can

26 November 2026, 12:35 UTC. Results of `production_fast_a` (predicted in 0022) and of Account 1's
training-noise batches (predicted in 0018). Instance 62662296.

## `production_fast_a`, iteration 6,000: 16 commands, 32 seeds each

512 of 512 pass, no falls. Checkpoint hash (SHA-256, first 16): `99178a6af71ad0c7`.

| Command | Speed reached | Largest tilt | Motor check (green / amber / red) |
|---|---|---|---|
| stand | 0.000 m/s | 2.2° | 1 / 31 / 0 |
| forward 0.12 m/s | 0.116 m/s | 4.3° | 0 / 32 / 0 |
| forward 0.31 m/s (0.7 mph) | 0.305 m/s | 5.8° | 0 / 32 / 0 |
| forward 0.36 m/s (0.8 mph) | 0.353 m/s (0.79 mph) | 6.1° | 0 / 32 / 0 |
| forward 0.36 m/s, shoved at 0.10 m/s | 0.353 m/s | 6.3° | 0 / 32 / 0 |

- The other eleven commands pass on all 32 seeds, almost all amber. Amber is a torque peak at the limit for a
  short time (at most 0.2% of an episode, at stand); `production_plain_a` is amber at 0.12 m/s too.
- Training: 590,253 episodes, 1,134 falls (`production_plain_a`: 104 falls), 71 minutes.
- The first checkpoint that passes every command is iteration 1,500 (`production_plain_a`: 375). Walking starts
  at 525 to 725; from 375 to 1,400 the two stand commands fail on all 64 episodes with the label `wander`.

## Shoved and hit while walking at 0.8 mph (iteration 6,000, episodes that stay up, of 32)

| | Shove 0.5 m/s | 1.0 m/s | 1.5 m/s | 2.0 m/s | Ball 3 m/s | 4 m/s | 5 m/s | 6 m/s |
|---|---|---|---|---|---|---|---|---|
| forward 0.36 m/s | 32 | 32 | 21 | 14 | 30 | 22 | 20 | 19 |
| forward 0.08 m/s | 32 | 32 | 28 | 15 | 32 | 15 | 16 | 6 |
| stand | 32 | 32 | 28 | 12 | 32 | 20 | 3 | 9 |
| `production_plain_a`, forward 0.08 m/s | 32 | 32 | 26 | 12 | 32 | 19 | 16 | 7 |

At 0.8 mph a shove of 1.5 m/s knocks it over more often than at the slow walk, and the ball less often.

## The hips turn faster than the servo's speed limit

The servo's speed limit is 9.6 rad/s (`velocity_limit_sim`, robot README). From the full-detail recordings
(4 seeds a command, after the first 5 s, 100 Hz), with `joint_speed.py` (the orb's scripts):

| Checkpoint | Command | Largest leg joint speed | Time with some leg joint over 9.6 rad/s | Worst joint |
|---|---|---|---|---|
| `production_fast_a` 6000 | 0.12 m/s | 8.1 rad/s | 0% | |
| `production_fast_a` 6000 | 0.31 m/s | 12.3 rad/s | 15.7% | front-left hip lift, 11.2% of the time |
| `production_fast_a` 6000 | 0.36 m/s | 13.1 rad/s | 22.3% | front-left hip lift, 14.1% of the time |
| `fast_narrow_s1` 1500 | 0.36 m/s | 8.7 rad/s | 0% | |
| `fast_s1` 1500 | 0.36 m/s | 9.6 rad/s | 0% | |
| `production_plain_a` 6000 | 0.12 m/s | 7.4 rad/s | 0% | |

- The simulator does not hold a joint to the limit: the policy trained with disturbances found a walk that
  swings the hip-lift joints up to 36% faster than the servo's figure. A real servo would lag there.
- The probe without disturbances (`fast_narrow_s1`) walks the same speed inside the limit, with shorter steps
  (59 mm a touchdown against 75 mm) taken more often (6.2 against 4.8 a second per foot).
- The motor check (`motor_mark`) counts time at the torque limit only, so it did not show this.
- 0021 said the legs "come within 10% of the speed limit" as if the limit held. It was not being enforced
  there either; those two runs happened to stay under it.

So `production_fast_a` is good footage of a 0.8 mph walk in simulation, and not yet a walk to put on a robot or
call the website candidate. The next production run needs a price on leg joint speed above the limit.

## Predictions of 0022

| Prediction | How sure | Result |
|---|---|---|
| Passes `forward_08mph` on 24 or more of 32 seeds. | 70% | Held: 32. |
| Mean speed of 0.33 m/s or more when told 0.36 m/s. | 60% | Held: 0.353 m/s. |
| Passes all 32 seeds of each of the 13 usual commands. | 75% | Held. |
| At 0.36 m/s more than half of the episodes are amber or red. | 60% | Held: 32 amber. |
| Shoved at 1.0 m/s while walking at 0.36 m/s, 28 or more of 32 stay up. | 50% | Held: 32. |
| The first all-pass checkpoint comes later than iteration 375. | 65% | Held: 1,500. |

What 0022 named as "wrong" did not happen: it does not park at the fast commands. What 0022 did not think of
did: it buys the speed with joint speeds the servo does not have.

## Account 1's training-noise batches (request 13, predicted in 0018)

Run after the fast-walk probes, 137 batches on the four production runs, 55,744 episodes. No errors.

- Skill 2 (forward slow and forward top, 64 episodes) for `production_a`: 0 passes up to iteration 250, 2 at
  275, 32 at 300 to 350, 64 at 375 and 400. Still a jump. Only `production_plain_a` has a part-way checkpoint
  (225: forward top 11 of 32).
- Fail labels on the two forward commands: `off_course` and `moonwalk`. Over all commands and runs:
  `off_course` 35,609, `jackhammer` 4,308, `treadmill` 2,865, `moonwalk` 1,388, `wander` 969, `yeet` 3.

| Prediction of 0018 | How sure | Result |
|---|---|---|
| For `production_a`, forward at top speed passes between 4 and 28 of 32 seeds at two or more checkpoints. | 60% | Wrong: at none. |
| The walking commands show three or more fail labels besides `statue`. | 70% | Wrong on the two forward commands (two labels); the curves and the diagonal have four. |

As 0018 warned: training's gradual climb came with the disturbances and changing commands on. Noise alone
does not make an "almost". `production_fast_a` has more of it without noise: its noise-free passes climb from
64 to 448 of 512 over iterations 525 to 725, with `statue`, `off_course`, `treadmill` and `wander`.

## In the shared record

- Sent 26 November: `fast_s1` (run 12), `fast_narrow_s1` (run 13), and request 13's rows for runs 7 to 10.
  Totals: 13 runs, 3,392 files, 407,224 episodes, 25,676 moments, 24 renders.
- `rows.py push --new-only` adds batches to a run without rewriting its rows. A plain second send of the four
  production runs grew a local copy of the database by 130 MB of dead rows.
- The local copy, vacuumed, with what the record holds now: 305 MB.

## Two things about the orb

- This orb sleeps between turns, and the copy-out service sleeps with it. From 11:50 to 12:18 UTC nothing was
  copied. Copies only move while a turn is running.
- GPU to orb runs at about 4.5 MB/s with two streams. `production_fast_a` is 6.4 GB.
