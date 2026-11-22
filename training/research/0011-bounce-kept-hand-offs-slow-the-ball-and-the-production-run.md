# 0011 · Body bounce is kept, hand-offs slow learning, a real ball, and the production run's predictions

22 November 2026, 09:02 UTC. GPU hours used so far: about 7.7. Written before `production_a` starts.

## `l2_bounce_s1` (rung 2 + `body_bounce`, weight -2.0) against 0008

| | Rung 2 | Rung 2 + body bounce |
|---|---|---|
| Passed of 416 | 416 | 416 |
| `body_bounce`, forward 0.12 m/s | 0.021 | 0.003 |
| Largest tilt, walking commands | 3.6° | 2.9° |
| Highest mean motor torque, standing / walking | 0.24 / 0.17 N·m | 0.14 / 0.19 N·m |
| Lift-offs per foot per second | 3.5 | 4.0 |
| Share of time on the floor, per foot | about 0.6 | 0.60 to 0.68 |
| Green / amber / red | 416 / 0 / 0 | 416 / 0 / 0 |

- **Predicted (70%): no visible change. Wrong: it is better.** The body is seven times steadier, and told to stand
  it now uses 0.14 N·m, close to the 0.13 N·m the plain stance needs (0008); rung 2 stood in a pose that cost
  0.24. The steps are a little quicker (4.0 against 3.5 a second).
- **Kept.** It is the only term after rung 2 that improved the look without costing a test.
- **The recipe: tracking, action change, a price on falling, leg torque, body bounce.** `l2_fidget_s1` is still
  running; with the stance already at its cheapest it is not expected to add anything, and the production run
  does not wait for it. If it does improve on this recipe, it goes into seeds B and C and is reported.

## `walk_g2_s1` (rung 1 + arm poses + hand-offs) against 0007

- **Predicted (65%): 400 or more pass, gait numbers within 15% of rung 1. The first is right, the second wrong.**
  416 of 416 pass, but 288 episodes are red and 128 amber, with 7.0 lift-offs per foot per second.
- **Hand-offs slow learning about three times.** Tracking reward reached 0.65 a second at iteration 100 without
  them (`walk_g1_s1`) and at iteration 300 with them. At 500 the policy has only just learned to follow commands
  and has not yet been smoothed by the penalties; `walk_g1_s1` looked the same at iteration 150.
- One seed each, and the three baseline seeds differed two-fold in when they took off (90, 140, 180), so part
  of this may be the seed. Not separated here.
- **Consequence:** 500 iterations is too short to judge the later groups by their final gait. The remaining
  group probes (G3 to G8) are read for one thing only: does tracking still rise, and does anything fall or
  blow up. The production run is long instead.

## Skill 5 with a real ball

Account 1 asks for a real simulated ball ("what the viewer sees is what happened") and three hits from
different sides. `evaluate.py --ball_speeds` now does that (batch `ball`, cells such as `stand_ball_400`):

- A ball (default 500 g, 40 mm radius, coral) waits on the floor 0.8 m from the robot, on the seed's shove side.
  At 5, 10 and 15 s it is thrown at the middle of the body from wherever it lies, so the three hits come from
  different sides and a recording has no cut and no jump. Between throws its speed is multiplied by 0.95 every
  0.02 s so that it stays near; a throw and the 0.4 s after it are left to the physics.
- The ball's position is in `poses.npz` (`ball_pos`) and in the 100 Hz recording; `render.py` draws it.
  Each hit is in the episode's `pushes` with the ball's speed and mass, its direction, and the change in the
  robot's speed that followed.
- Test: no fall, which is "still standing 3 s after each of three hits". While the ball is within 0.25 m of
  the body, contact on the body counts as a fall only if the body is under 35 mm high (the ball is not the floor).
- Checked: the default evaluation gives the same numbers as before the change (rung 1, 8 seeds, three cells).

Falls of 32 at the final checkpoint, walking forward / told to stand:

| Ball speed | Tracking only (`baseline_v2_s1`) | Rung 2 (`ladder2_s1`) |
|---|---|---|
| 3 m/s | 7 / 0 | 0 / 0 |
| 4 m/s | 27 / 25 | 12 / 10 |
| 5 m/s | 26 / 30 | 18 / 27 |
| 6 m/s | 31 / 31 | 19 / 31 |

- Across all eight cells the untrained robot survives more often (160 of 256) than rung 2 (142) or the baseline
  (79): it stands on four feet. The same was seen with the plain shove (0006). No run so far was trained with shoves.
- Labels: `yeet`, `faceplant`, a few `turtle` and `tumble`.
- Every recorded run from now on gets this ladder at five checkpoints (3, 4, 5, 6 m/s).

## The production run, seed A (`production_a`)

- Task `Scorbi-Velocity-Flat-Production`: the recipe above with all eight disturbance groups of 0007
  (arm, hand-offs, shoves, friction, mass, motors, delay, wider resets). Seed 1, 4,096 robots, 6,000 iterations.
- **A departure from the plan, on purpose:** the plan adds the groups one at a time before the long run. Only
  G1 and G2 have been read; G3 to G8 are still running as probes beside it. They cannot give a verdict at 500
  iterations (above), and waiting for them would leave the long run until the afternoon. If a probe shows a
  group that stops tracking from rising or makes robots fall, the production run is stopped and restarted
  without that group.
- It starts as a third job, so it runs at about half speed until the probe queues end.

| Prediction | How sure |
|---|---|
| Tracking takes off later than in any probe: after iteration 500. | 70% |
| Final checkpoint, nominal robot: 400 or more of 416, no red, body bounce under 0.02, under 4.5 lift-offs per foot per second. | 50% |
| The ball at 4 m/s: falls drop from rung 2's 22 of 64 to under 10. The 1.5 m/s shove: under 12 of 32 on each command. | 55% |
| An earlier checkpoint falls to a ball the final one survives (Account 2's request). | 70% |
| In the website's simulator the parked share on slow forward falls under 10% (rung 2: 19%). | 45% |

Wrong would be: under 375 passes or more than 10% red at the final checkpoint. Then the groups are bisected
with the G probes, and the recipe is run without disturbances as the fallback policy.
