# 0015 · The plain recipe wins on the website, fidget does not brace, and the GPU queue is done

22 November 2026, 20:57 UTC. GPU hours used so far: about 19.5. Nothing is training. Every run below finished
with all exits 0.

## The choice between the two production recipes (0012's predictions)

Final checkpoints. The first block is the per-command test on the training simulator's flat floor (32 seeds);
the second is the website's simulator on the page's bumpy floor (8 seeds per command, 13 commands).

| | `production_a` (with body bounce), 6,000 | `production_plain_a` (rung 2 alone), 6,000 | `production_b` (with body bounce, seed 2), 3,000 |
|---|---|---|---|
| Per-command test | 416 of 416 | 416 of 416 | 416 of 416 |
| First checkpoint that passes 90% | 375 | 325 | 425 |
| Falls in training | 18 of 589,830 episodes | 104 of 589,868 | 14 of 294,917 |
| Forward at 0.12 m/s | 0.125 | 0.117 | 0.122 |
| Foot lift | 3.8 mm | 7.4 mm | 3.0 mm |
| Body bounce | 0.005 | 0.028 | 0.010 |
| Standing torque | 0.02 N·m | 0.11 N·m | 0.02 N·m |
| Motor check | 154 green, 262 amber | 129 green, 287 amber | 54 green, 362 amber |
| Website: falls | 0 of 104 | 0 of 104 | 0 of 104 |
| Website: commands parked over 5% | **7 of 11** | **2 of 11** | 8 of 11 |
| Website: forward 0.12, slow forward 0.06 | 0.099, 0.026 | 0.116, 0.049 | 0.086, 0.017 |

- **Predicted (60%): the plain recipe lifts its feet 1.5 mm or more higher and bounces twice as much or more.**
  Right: 7.4 mm against 3.8 mm, and 0.028 against 0.005.
- **Predicted (55%): on the website the plain recipe has fewer commands over 5% parked.** Right: 2 against 7.
  Seed 2 of the bounce recipe parks on 8, so it is the recipe and not one seed.
- **Decision: the candidate for the website is `production_plain_a` at iteration 6,000.** It does not pass the
  website test yet: backward parks 20% of the time (0.059 of 0.10 m/s) and slow forward 6%. No fall anywhere.
- **For clips on the flat floor both walk.** The plain recipe's steps are visible (7.4 mm); the bounce recipe
  is steadier but shuffles (3.8 mm). 0011's "body bounce is kept" is withdrawn for the website and left open
  for clips.
- **The amber marks are one-step peaks, not strain.** In every production run the median episode touches the
  1.18 N·m limit for 0.1% of the time while the worst joint averages 0.18 to 0.21 N·m. No episode is red. The
  500-iteration runs without disturbances were all green; which disturbance causes the peak is not tested.

## `production_fidget_a` against 0014

| Prediction | Result |
|---|---|
| 8 falls or fewer of 64 to the 4 m/s ball (50%) | **Wrong: 25** (15 walking, 10 standing). `production_b`: 37; `production_a`: 26. |
| 410 or more of 416 pass (65%) | Right: 415 (one seed of slow forward stands still). |
| Tracking reward below `production_b`'s 1.27 at iteration 3,000 (55%) | 1.265 against 1.270: no real difference. |

- Fidget's one fall in 64 at 500 iterations (0013) did not carry over to a run trained with disturbances.
  At 5 m/s it falls 43 of 64 and at 6 m/s 54. Shove at 1.5 m/s: 10 walking, 4 standing.
- On the website it is the worst of the four: 8 commands parked, backward 62%.
- **Not kept.** No recipe of this session stands up to the 500 g ball at 4 m/s more than about 6 times in 10.

## What skill 5 has to show

- At 3 m/s every checkpoint of every run survives all three hits, the untrained one too (it stands on four feet).
- At 4 m/s `production_a` falls 0 of 64 untrained, 46 at iteration 200 and 26 at 6,000; under the 1.5 m/s
  shove 0, 20 and 12. So "an earlier checkpoint that the same hit knocks over" exists seed by seed, between
  iteration 200 and the final checkpoint, at 50 Hz. Only the final checkpoint's hits are in full detail; the
  earlier one can be recorded again from its checkpoint and seed.

## The swarm, the What If, and Account 2's one-line change

- **Swarm (100 robots, stand and forward at top speed):** `production_a` 100, 198, 200, 200, 200 of 200 at
  iterations 0, 275, 300, 350, 6,000; `production_plain_a` 100, 200, 200, 200, 200 at 0, 225, 275, 300, 6,000.
- **`whatif_tall_s1` (paid only for being tall, 500 iterations):** 3 of 416 pass, no falls. It ignores every
  command, leans to about 58°, backs away at 0.45 m/s and spins at 3.7 rad/s, red on the motor check throughout.
- **Account 2's "one reward line changed" needs no extra run.** Four pairs already recorded differ by one line,
  same robot, seed and length: `baseline_v2_s1` against `whatif_tall_s1` (tracking becomes tall) and against
  `stock_reward_s1` (the tracking width); `ladder2_s1` against `l2_drag_s1` (foot drag added: it parks on
  three feet); `ladder1_s1` against `ladder1_steps_s1` (long steps added: it hops).

## State of the session

- Queue items 1, 2, 4, 5, 6, 9 and 10 have their runs; 3, 7 and 8 were set aside for a later session.
- Open, not started: the plain recipe's backward walk on the website's floor. Training on a floor with
  bumps is the direct test and is a new task, so it waits for the owner.
- The orb was paused again from about 19:25 to 20:40 UTC with an upload half done; the stuck upload was
  restarted at 20:43. The GPU has been idle since 20:47.
