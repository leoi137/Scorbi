# 0006 · The corrected baseline on three seeds, the shove ladder, and the website test again

22 November 2026, 07:08 UTC. GPU hours used so far: about 5.8.

## The corrected baseline, three seeds

`baseline_v2_s1`, `_s2`, `_s3`: tracking only, corrected joint limits and clamped targets (0004), seeds 1, 2, 3,
500 iterations each. Final checkpoint, 13 commands × 32 seeds.

| Seed | Passed of 416 | First checkpoint with 90% passing | Forward at 0.12 | Turn at 1.0 | Action flip rate | Red on the motor mark | Lift-offs per foot per second |
|---|---|---|---|---|---|---|---|
| 1 | 416 | 90 | 0.119 m/s | 0.99 rad/s | 0.17 | 100% | 8.2 |
| 2 | 416 | 180 | 0.119 | 0.98 | 0.19 | 100% | 7.9 |
| 3 | 416 | see `summarize.py` | — | — | — | 100% | — |

- **Prediction (0003): same verdict on three seeds, speeds within 30%. Right.** All three pass every command in
  32 of 32 seeds at the end. They differ in how fast they get there (90 against 180 iterations) and in how much
  they drift when told to stand (11 mm against 56 mm in 20 s).
- All three have the same fault: every episode is red on the motor mark, and the feet buzz at about 8 lift-offs a second.
- The do-nothing control passes 64 of 416 on each (the two stand commands).
- In training, `baseline_v2_s1` fell once in 49,152 episodes. No robot was thrown or lost
  (`non_finite_rewards_total` 0, `blow_up` 0) in any run after the fix.

## The shove ladder

At the plan's shove (0.10 m/s) nothing happens: no fall at any checkpoint of any run. So the two shoved
commands were repeated at harder shoves on `baseline_v2_s1`, 32 seeds each (batch `extra`, cells such as
`forward_shoved_150` for 1.5 m/s). The shove is a step change in the body's speed; no ball is simulated.

Falls of 32, walking forward / told to stand:

| Shove | Untrained (0) | Iteration 60 | Iteration 100 | Final (500) |
|---|---|---|---|---|
| 0.5 m/s | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 1.0 m/s | 0 / 0 | 4 / 0 | 5 / 0 | 3 / 0 |
| 1.5 m/s | 0 / 0 | 18 / 12 | 19 / 19 | 23 / 21 |
| 2.0 m/s | 10 / 10 | 22 / 29 | 29 / 29 | 30 / 26 |
| 3.0 m/s | 24 / 24 | 30 / 32 | 32 / 32 | 32 / 32 |

- **This is where the falls are.** Labels: `faceplant` and `yeet`, one `turtle`. A 1.5 m/s shove is 1.9 N·s, about
  what a 60 g ball at 30 m/s would give, so "THE SHOVE" needs a far harder hit than the plan assumed.
- **The untrained robot takes a shove better than the trained one.** At 1.5 m/s the untrained robot, which just
  stands on four feet, never falls; the trained one falls 21 to 23 times of 32. The trained policy keeps two
  feet in the air most of the time. Nothing in its reward ever asked it to survive a shove: training has no
  shoves yet (plan 5.5 adds them after the baseline).
- An earlier checkpoint where the same shove knocks it over, which Account 2 asked for, does not exist in this
  run: the later checkpoints fall more, not less. It needs a run trained with shoves.
- From commit `bead06a` every recorded run gets this ladder (0.5, 1.0, 1.5, 2.0 m/s) at five checkpoints.

## The website test on the corrected baseline

`baseline_v2_s1` iteration 500 in the website's own simulator: v0.5 model, 0.002 s steps, the page's uneven
floor, 8 seeds per command, the same starts as the training evaluation.

| Command | Website simulator | Training simulator | Parked share on the website |
|---|---|---|---|
| Forward 0.12 m/s | 0.109 | 0.119 | 1% |
| Forward 0.06 m/s | 0.052 | 0.062 | 7% |
| Backward 0.10 m/s | 0.090 | 0.104 | 3% |
| Sideways 0.08 m/s | 0.058 and 0.073 | 0.079 and 0.081 | 11% and 2% |
| Turn 1.0 rad/s | 0.95 and 0.95 | 0.99 and 1.03 | 0% |
| Curve 0.08 m/s with 0.5 rad/s | 0.074 with 0.41, 0.068 with 0.44 | 0.085 with 0.49 | 6% and 7% |
| Diagonal 0.07 with 0.05 m/s | 0.060 with 0.033 | 0.072 with 0.049 | 21% |
| Falls | 0 of 104 | 0 of 416 | |

- No falls. Speeds are 85 to 95% of the training simulator's on most commands; sideways-left and the diagonal are lower.
- **It would not pass the plan's gate (part 8.4):** the parked share is over 5% on five commands, and every
  episode is red on the motor mark. Expected of a tracking-only probe trained on a flat floor.
- The slow-forward stall seen with the pre-fix baseline (0.021 m/s, parked 42%) is gone: 0.052 m/s, parked 7%.
