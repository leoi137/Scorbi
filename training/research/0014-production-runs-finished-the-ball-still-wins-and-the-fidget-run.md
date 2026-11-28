# 0014 · The production runs finished, the ball still wins, and the fidget run starts

22 November 2026, 19:15 UTC. GPU hours used so far: about 17.8. Written before `production_fidget_a` starts.

## A gap in the session

All training and every evaluation finished at 12:22 UTC. The orb that watches the runs was paused from 09:46
to 19:09 UTC, so nothing was read, copied or started for about 6.8 hours while the instance stayed on (about
$1.20). The four runs below were complete on the GPU but not yet copied out; the copy resumed at 19:10. A
check-in every 90 minutes is now set.

## The four runs, from their logs (full comparison in the next entry, once they are copied)

| Run | Iterations | Per-command test at the final checkpoint | Training exit and five evaluations |
|---|---|---|---|
| `production_a` (recipe, all eight groups, seed 1) | 6,000 | 416 of 416, no falls | all exit 0 |
| `production_plain_a` (no body bounce, seed 1) | 6,000 | 416 of 416, no falls | all exit 0 |
| `production_b` (recipe, seed 2) | 3,000 | 416 of 416, no falls | all exit 0 |
| `whatif_tall_s1` (paid only for being tall) | 500 | 3 of 416, no falls; 215 labelled `moonwalk` | all exit 0 |

- **0012's third prediction holds:** `production_b` passes the same commands as `production_a` (all of them).
- 0012's other two (foot height, bounce, the website test) need the copied runs.

## The ball and the shove at the final checkpoint

Falls of 32, walking forward / told to stand.

| | `production_a` | `production_plain_a` | `production_b` |
|---|---|---|---|
| Ball 3 m/s | 0 / 0 | 0 / 0 | 0 / 0 |
| Ball 4 m/s | 11 / 15 | 13 / 16 | 21 / 16 |
| Ball 5 m/s | 14 / 27 | 16 / 27 | 20 / 25 |
| Ball 6 m/s | 24 / 21 | 25 / 22 | 28 / 24 |
| Shove 1.5 m/s | 8 / 4 | 6 / 7 | 8 / 10 |
| Shove 2.0 m/s | 25 / 19 | 20 / 21 | 21 / 20 |

- **Both of 0013's predictions are wrong.** `production_a` falls 26 times of 64 to the 4 m/s ball (predicted
  4 or fewer, 45%) and 41 of 64 at 5 m/s (predicted fewer than 20, 50%).
- Six thousand iterations of shoves up to 1.0 m/s did not brace it against the ball: it does no better than
  the 500-iteration runs that were never shoved (18 to 27 of 64 at 4 m/s in 0013).
- So 0013's rule fires: one run of the production recipe + `fidget_at_rest` is trained.

## `production_fidget_a`

Task `Scorbi-Velocity-Flat-Production-Fidget`: `production_a` plus `fidget_at_rest` (weight -0.2), seed 1,
3,000 iterations, alone on the GPU. It is compared with `production_b` (same length) on the ball, the
per-command test and the website test.

| Prediction | How sure |
|---|---|
| It falls 8 times or fewer of 64 to the 4 m/s ball at its final checkpoint (`production_b`: 37). | 50% |
| It passes 410 or more of 416 on the per-command test. | 65% |
| It stands in training more than it should: tracking reward at iteration 3,000 below `production_b`'s 1.27. | 55% |
