# 0009 · Long steps and rung 4 both end in hopping; a paired-steps probe

22 November 2026, 08:08 UTC. GPU hours used so far: about 6.8. Written before `l2_paired_s1` starts.

## `ladder1_steps_s1` against 0007

Rung 1 plus `long_steps` (weight 25). Final checkpoint.

| | Rung 1 | Rung 1 + long steps |
|---|---|---|
| Passed of 416 | 416 | 355 |
| Forward at 0.12 m/s | 0.118 | 0.101 |
| Share of time each foot is on the floor | about 0.6 | 0.22 |
| Share of time with three or more feet down | 0.28 | 0.02 |
| Lift-offs per foot per second | 3.6 | 3.8 |
| `body_bounce`, forward 0.12 m/s | 0.027 | 0.293 |
| Largest tilt, walking commands | 5.7° | 9.9° |
| Red on the motor mark | 0% | 100% |

- **Predicted:** swing 0.15 s or more (right: about 0.2 s), under 3 lift-offs a second (wrong), 400 or more
  pass and green (wrong on both), slow forward not parked (right: 0%).
- **It hops.** Each foot is in the air for 0.2 s and on the floor for 0.06 s. The term earned 0.63 a second in
  training, more than the 0.4 priced for the scripted gait: the price assumed two swings a second per foot,
  and four fit when the stance is cut to almost nothing. Told to stand it wanders (32 of 32).
- **Not kept.** The mistake was mine: the term pays for time in the air and says nothing about time on the floor.
- It is a recorded failure worth showing: "paid for long steps, it learned to hop".

## `ladder4_s1` (rung 3 + `foot_drag`) against 0005

- 416 of 416 pass, and every episode is red on the motor mark. Each foot is on the floor 21 to 26% of the time;
  three feet are never down together. `body_bounce` 0.184 (rung 2: 0.021); tilt up to 8°.
- **Predicted (45%): feet lift 8 mm or more; 40% that slow forward parks.** Lift: see `summarize.py` once the
  recording is copied. Slow forward does not park (0%).
- With rung 3 this makes three terms in a row that were won the same way: `foot_slip`, `foot_drag` and
  `long_steps` all cost nothing for a foot that is in the air, so the policy keeps its feet in the air.
- Rung 3's walk does lift its feet clearly (21 mm against 8 mm, swing 0.14 s against 0.10 s). What rules it out
  is the body (five times the bounce), the motors (amber) and a splayed stance when told to stand.

## Probe: paired steps (`l2_paired_s1`)

- **One change from rung 2:** `+ paired_steps`, weight 15. As `long_steps`, but a swing is only paid when the
  foot stood on the floor at least as long as it then swung. A hop (0.06 s down, 0.2 s up) pays nothing.
- **Price.** The scripted gait (each foot 0.2 s down, 0.2 s up) earns 0.3 a second. Rung 2's patter (0.10 s
  swings) earns nothing. Marching on the spot when told 0.06 m/s would earn 0.79 + 0.3 = 1.09 against 1.5 for
  walking.
- Runs as a third job beside the two queues, so all three are slower for about 25 minutes.

| Prediction | How sure |
|---|---|
| Swing time rises from 0.10 s to 0.14 s or more, with each foot on the floor at least 45% of the time. | 45% |
| Still 400 or more of 416, no red. | 60% |
| Otherwise it changes nothing (the term is too weak to move rung 2's gait), rather than breaking it. | 35% |

Wrong would be: hopping again (a foot on the floor under 35% of the time), or under 375 passes.
If it changes nothing or breaks the walk, cadence is left alone for this session: rung 2's gait is the recipe's.
