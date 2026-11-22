# 0012 · Fidget is not kept, shoves train, body bounce costs on the website's floor, and a comparison run

22 November 2026, 09:29 UTC. GPU hours used so far: about 8.2. Written before `production_plain_a` and
`production_b` start. `production_a` is at iteration 1,400 of 6,000 with tracking at 1.2 of 1.5 a second.

## `l2_fidget_s1` (rung 2 + `fidget_at_rest`, weight -0.2) against 0008

- **Predicted (60%): no visible change when walking; standing torque under 0.24 N·m and drift under 10 mm.**
  Standing is right: 0.10 N·m and 2 mm of drift in 20 s, the stillest stand so far.
  Walking is slightly worse, not unchanged: body bounce 0.032 against 0.021, tilt 4.3° against 3.6°.
  414 of 416 pass (one seed of one command stands still), 415 green.
- **Not kept.** The test went down by two and the walk did not improve. `body_bounce` already brings the
  stand to 0.14 N·m.

## `walk_g3_s1` (rung 1 + arm poses + hand-offs + shoves of 0.2 to 1.0 m/s) against 0007

- 416 of 416 pass on the nominal robot; 388 amber, none red. Tracking takes off around iteration 300, as with
  hand-offs alone (0011). 60 falls in 49,173 training episodes.
- The prediction was about the shove ladder and the ball (falls at 1.5 m/s under 12; more feet on the floor).
  Those two evaluations are running; the next entry has them. Share of time with three or more feet down: 0.33
  (rung 2: 0.35), so no change there at 500 iterations.

## Body bounce on the website's floor

`l2_bounce_s1` iteration 500 in the website's simulator, against rung 2 (0010). 8 seeds per command; no falls
and every episode green in both.

| Command | Rung 2: speed, parked | Rung 2 + body bounce: speed, parked |
|---|---|---|
| Forward 0.06 m/s | 0.046, 19% | 0.050, 10% |
| Forward 0.12 m/s | 0.115, 0% | 0.105, 4% |
| Backward 0.10 m/s | 0.091, 0% | 0.084, 4% |
| Sideways left 0.08 m/s | 0.057, 8% | 0.047, 20% |
| Sideways right 0.08 m/s | 0.076, 0% | 0.076, 0% |
| Curves 0.08 m/s with 0.5 rad/s | 0.076 and 0.075, 0% | 0.072 and 0.070, 2% and 6% |
| Forward 0.08 m/s, shoved | 0.074, 1% | 0.057, 13% |

- **With body bounce four commands miss the gate (parked under 5%); with rung 2 alone, two.** On the flat floor
  of the training simulator the two are equal on speed, and bounce is steadier (0011).
- The likely reason, not tested by itself: bounce lifts its feet 6.3 mm against 8.3 mm, and the page's floor
  has mounds of 6 to 14 mm. 8 seeds per command is a small sample.
- So 0011's "kept" needs a second look once both recipes have been trained with the disturbances.

## What runs next, and what is dropped

- **`production_plain_a`:** the comparison. Rung 2 alone with all eight groups, seed 1, 6,000 iterations: the
  same as `production_a` without `body_bounce`. The recipe is chosen between the two on the website test and
  the look on the flat floor.
- **`production_b`:** seed 2 of `production_a`'s recipe, 3,000 iterations (block F).
- **Dropped: the group probes G4 to G8.** `production_a` already trains with all eight groups on: tracking was
  0.67 a second at iteration 340 and 1.18 at iteration 960, with no robot lost. That answers what those probes
  were for (does a group stop the walk from being learned), and G2 and G3 showed that 500 iterations cannot
  say more. This departs from the plan's "one group at a time"; the GPU time goes to the two runs above.
- `whatif_tall_s1` runs after `production_b`.

| Prediction | How sure |
|---|---|
| `production_plain_a` lifts its feet higher than `production_a` at the final checkpoint (by 1.5 mm or more) and bounces more (by twice or more). | 60% |
| In the website's simulator the plain recipe has fewer commands over 5% parked than the bounce recipe. | 55% |
| `production_b` passes the same commands as `production_a` at iteration 3,000. | 60% |
