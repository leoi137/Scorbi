# 0005 · The reward ladder: prices and predictions (block D)

22 November 2026, 06:35 UTC. Written before any ladder run starts. The six runs are queued behind block C.

## Why

The tracking-only baseline follows every command (0004) but walks by buzzing: each foot lifts off 8.7 times a
second, lifts about 3 mm, and a leg motor sits on its 1.18 N·m limit half the time. The ladder (plan 5.4) adds
one penalty per run. Code: `scorbi_lab/ladder.py`, commit `c05724f`. Each rung is its own task name,
`Scorbi-Velocity-Flat-Ladder1` to `Ladder6`, seed 1, 500 iterations.

From this commit on, every run logs every ladder term as a number, rewarded or not: `measured_terms` in
`iterations.jsonl` and in every evaluation episode.

## Prices

Tracking pays up to 1.5 a second. Each weight was set so the term costs the buzzing baseline 0.1 to 0.6 a
second and a clean walk close to nothing. Values are from the 100 Hz recordings of `baseline_s1` at iteration 500.

| Rung | Term | What it measures | Baseline value (forward, turn) | Weight | Cost to the baseline per second |
|---|---|---|---|---|---|
| 1 | `action_rate` | Change in the 12 actions between control steps, squared and summed | 3.1, 6.2 | -0.05 | 0.16 to 0.31 |
| 2 | `leg_torque` | Leg motor torques, squared and summed | 5.6, 7.4 N²m² | -0.05 | 0.28 to 0.37 |
| 3 | `foot_slip` | Speed along the floor of feet that are on the floor, summed | 0.12, 0.08 m/s | -1.0 | 0.08 to 0.12 |
| 4 | `foot_drag` | A foot moving along the floor without being lifted toward 16 mm | about 2 (my arithmetic) | -0.3 | about 0.6 |
| 5 | `body_bounce` | Vertical body speed squared plus a tenth of roll and pitch rate squared | 0.07 | -2.0 | 0.14 |
| 6 | `fidget_at_rest` | Leg joints away from the stance when told to stand | about 2.3 rad (my arithmetic) | -0.2 | about 0.46, stand commands only |

- **Rung 1 also adds a price on falling** (`fell`, 8 off per fall). The plan asks for it with the first penalty:
  otherwise ending the episode stops the penalties. The baseline falls once in 49,152 episodes, so it changes almost nothing.
- **Known risk: the sum is heavy.** With all six on, the baseline's gait would lose about 1.5 a second, as much as
  tracking pays. A robot told to walk slowly (0.06 m/s) earns 0.79 a second for standing still. If the policy
  does not find a cheaper gait, it parks. The parked share per command at each rung will show it.
- **Exploration is taxed too.** With the starting action noise (1.0) `action_rate` reads 24, which is 1.2 a second.
  The baseline shrank its own noise to 0.06 by the end, so this is expected to pass quickly.
- `step_time` (paid at each touchdown for time in the air, up to 0.2 s) is measured on every run but is not on
  the plan's ladder. It is the next probe if the steps stay too quick after rung 4.

## Predictions

| Rung | Prediction | How sure |
|---|---|---|
| 1 `action_rate` | Flip rate under 0.08 (baseline 0.15). Still passes 390 or more of 416. Foot lift-offs fall below 5 a second. Motors still mostly red. | 60% |
| 2 `leg_torque` | Most episodes leave red: under half red at iteration 500. Speeds drop by under 15%. | 55% |
| 3 `foot_slip` | Small change. Slip halves; nothing else moves much. | 60% |
| 4 `foot_drag` | Feet lift 8 mm or more in swing. This is the rung most likely to cause parking on the slow forward command. | 45% that it lifts, 40% that slow forward parks |
| 5 `body_bounce` | Body steadier; largest tilt under 2.5° on walking commands. | 55% |
| 6 `fidget_at_rest` | Stand passes 32 of 32 with drift under 2 cm. | 65% |
| Whole ladder | At least one rung has to be re-priced before the recipe is chosen. | 75% |
