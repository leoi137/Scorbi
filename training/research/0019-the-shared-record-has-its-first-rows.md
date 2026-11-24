# 0019 · The shared record has its first rows, and the first requests are answered

24 November 2026. The instance is still stopped; nothing here used the GPU.

## What was sent

The owner applied the training-record migration to the shared database on 24 November (website repo, PR #35).
Rows for 11 runs are in the `training_*` tables: the pilot, the four production runs, `whatif_tall_s1`, and
the five runs the production runs descend from (`baseline_s1`, `baseline_v2_s1`, `ladder1_s1`, `ladder2_s1`,
`l2_bounce_s1`), which have to be there as parents.

| Table | Rows |
|---|---|
| `training_runs` | 11 |
| `training_files` | 2,460 |
| `training_iterations` | 21,017 |
| `training_checkpoints` | 616 |
| `training_episodes` | 283,480 |
| `training_moments` | 15,897 |
| `training_renders` | 22 |

- Read back after sending: every count equals the row files; `training_checkpoint_stats` gives `production_a`
  forward at top speed 0 of 32 at iteration 250 and 32 of 32 at 275; a ball moment resolves to its Drive file.
- The other 12 runs of the session (the failed recipes and the probes) are in Drive and have no rows yet.

## Slim rows, because the database's room is not known

- The full rows measured 613 MB for 14 runs (0016). The rows sent are slim (`rows.py build --slim`): 206 MB for
  these 11 runs, measured in a local Postgres. Episodes are 172 MB of it, iterations 27 MB.
- An episode of the fixed-seed batch that is not a picked moment keeps no `numbers` (241,087 of 283,480 rows).
  The others keep nine: speed achieved, parked share, largest tilt, time upright, distance along the command,
  fall cause, peak and mean torque, share of time at the limit. The ball's description is once in each run's
  manifest. Everything left out is in each checkpoint's `episodes.json` in Drive.
- Sending the full rows later fills the numbers in. That rewrites every episode row, so the table grows by
  about its own size until the database reclaims the space.

## What the test before sending found

The send (`rows.py push`) had only ever been checked with a loader of its own. It was run against a local
Postgres 17 with PostgREST 16.6 and a 1,000-row limit, as Supabase has, before anything went to production.

- **A clip named for the wrong command stopped a send half-way.** `l2_bounce_s1`'s two previews were rendered
  from episode 32, which is slow forward (0.06 m/s), and named `forward`. So the "candidate gait, forward" clip
  shown to the owner on 22 November was the slow-forward command, not 0.12 m/s. Correctly named copies are in
  Drive beside the old ones; a clip whose name matches no episode now gets a file row and no render row.
- **Moments would have been cut at 1,000 on a second send.** They are now read in pages and matched by episode,
  kind and seconds, so a send that is repeated, or resumed after breaking off, adds only what is missing.
  Checked: sending three runs twice left every count unchanged.
- **The pilot has no pass test.** It was recorded before the tests existed, and an episode row must say passed
  or failed, so its 312 episodes have no rows. Its run, files, iterations and checkpoints do, and the run's
  notes say where the episodes and the clip are.
- Checkpoints with a swarm batch were not marked `swarm`; they are now (set on the 15 rows directly).

## The requests

The account orbs added 20 requests. Status after reading each against the record:

| Status | Requests |
|---|---|
| Done from what is recorded | 2 (swarm), 3 (counters), 4 (final stand), 5 (reward terms), 6 (final walk, gait), 8 (one reward line changed), 9 (final shoves) |
| Accepted, waiting for the GPU | 13 (training-noise batches, Account 1's first), 1, 7, 10, 12, 15 |
| Open | 14 (skill 1, the owner's decision), 16 (the model files in Drive), 11 and 17 to 20 (skills of later sessions) |

- Request 8 asked for a new run; it is answered with `whatif_tall_s1` against its parent, as 0015 proposed.
- Requests 10 and 15 need full detail at iterations 0, 50, 100 and 200 of the shove and ball batches. Running
  those again writes into folders that already have rows pointing at them, so how to store the result is to be
  settled before they run.
