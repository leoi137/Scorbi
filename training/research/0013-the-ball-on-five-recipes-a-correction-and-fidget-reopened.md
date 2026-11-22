# 0013 · The ball on five recipes, a correction to 0011, and fidget reopened

22 November 2026, 09:41 UTC. GPU hours used so far: about 8.3. `production_a` is at iteration 1,930 of 6,000,
`production_b` at 260 of 3,000, `production_plain_a` at 155 of 6,000; all three train at once (about 1.5 s an
iteration each).

## Correction to 0011

The rung 2 column of 0011's ball table held iteration 200, not the final checkpoint. The total (142 of 256
survive) was right. The corrected column is below. 0011's prediction said "rung 2's 22 of 64" at 4 m/s; the
figure at the final checkpoint is 21 of 64.

## The ball and the shove at the final checkpoint (iteration 500), five recipes

Falls of 32, walking forward / told to stand. `l2_bounce_s1` finished before the ball was part of a recorded
run, so its ball ladder was run afterwards with the same settings (`/workspace/export/ball_bounce.sh`).

| | Tracking only | Rung 2 | Rung 2 + body bounce | Rung 2 + fidget | Rung 1 + arm, hand-offs, shoves (G3) |
|---|---|---|---|---|---|
| Ball 3 m/s | 7 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Ball 4 m/s | 27 / 25 | 4 / 17 | 9 / 9 | **1 / 0** | 4 / 23 |
| Ball 5 m/s | 26 / 30 | 16 / 28 | 15 / 28 | 14 / 21 | 17 / 25 |
| Ball 6 m/s | 31 / 31 | 21 / 28 | 26 / 31 | 21 / 30 | 19 / 28 |
| Shove 1.5 m/s | 23 / 21 | not run | 5 / 9 | **4 / 0** | 9 / 14 |
| Shove 2.0 m/s | 30 / 26 | not run | 21 / 25 | 25 / 15 | 27 / 24 |

- **`walk_g3_s1` against 0007 (under 12 falls of 32 at 1.5 m/s):** right walking (9), wrong standing (14).
  Being shoved in training for 500 iterations did not make it harder to knock over than runs that never were:
  it is behind (388 of 416 episodes amber, tracking took off at iteration 300). 500 iterations cannot judge
  shove training; `production_a` can.
- **Fidget is the best of the five against a hit when standing.** At 4 m/s it falls once in 64; the others
  fall 18 to 52 times. Paid to keep its joints still when told to stand, it stands planted.
- 0012 (written before these ladders finished) marked fidget "not kept" on the per-command test and the walk.
  That stands for the walk. For skill 5 it is reopened.

## Decision rule for fidget, set before `production_a`'s ladders

`production_a` is shoved while standing through 6,000 iterations, which may teach the same bracing.

- If `production_a`'s final checkpoint falls 4 times or fewer of 64 to the 4 m/s ball, fidget is not needed.
- If it falls more, one run of the production recipe + `fidget_at_rest` is trained for skill 5, started from
  scratch at 3,000 iterations, and compared on the ball, the per-command test and the website test.

| Prediction | How sure |
|---|---|
| `production_a` at its final checkpoint falls 4 times or fewer of 64 to the 4 m/s ball. | 45% |
| It falls fewer than 20 of 64 at 5 m/s (500-iteration runs: 35 to 44). | 50% |

## Size of the record

Sixteen runs' rows, loaded into a local Postgres with the PR #31 tables, take 450 MB in `training_episodes`
(18,128 rows a run, about 1.6 kB each, most of it the per-episode `numbers`). The long runs have about three
times the checkpoints. Nothing is sent to the shared database until the owner says how much room it has; the
same numbers are in each checkpoint's `episodes.json` on Drive either way.
