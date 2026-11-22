# 0010 · Foot drag parks the robot, paired steps fail, the first group probe, and rung 2 on the website

22 November 2026, 08:36 UTC. GPU hours used so far: about 7.2.

## `l2_drag_s1` (rung 2 + `foot_drag`) against 0008

- **Predicted (45%): swing lift rises to 11 mm or more without the feet-in-the-air trick. Wrong, and not by the
  trick either: it parks.** 64 of 416 pass (the two stand commands). It stands on three feet with the fourth held
  in the air for the whole episode (share of time on the floor: 1.0, 1.0, 1.0, 0.0), and does not move on any
  command. Every episode is amber. Labels: `statue`, `off_course`.
- In training its tracking reward fell to 0.37 a second (rung 2: 1.41). 0005 named this rung the one most
  likely to cause parking (40%).
- **Not kept.** As a recorded failure it is one of the clearest so far: "told not to drag its feet, it lifted
  one and never walked again".

## `l2_paired_s1` (rung 2 + `paired_steps`) against 0009

| | Rung 2 | Rung 2 + paired steps |
|---|---|---|
| Passed of 416 | 416 | 416 |
| Lift-offs per foot per second | 3.5 | 4.3 |
| Share of time on the floor, per foot | about 0.6 | 0.50, 0.51, 0.39, 0.34 |
| `body_bounce`, forward 0.12 m/s | 0.021 | 0.209 |
| Largest tilt, walking commands | 3.6° | 5.7° |
| Green / amber / red | 416 / 0 / 0 | 153 / 263 / 0 |
| What the term earned in training | | 0.015 a second (the scripted gait would earn 0.3) |

- **Predicted (45%): longer swings with each foot down at least 45% of the time. Wrong.** The steps got quicker,
  the body bounces ten times as much, and two thirds of the episodes are amber. The term itself earned next to nothing.
- **Not kept. Cadence is left alone for this session**, as 0009 said it would be in this case. Three attempts
  to shape the step (`long_steps`, `foot_drag`, `paired_steps`) each made the walk worse. A reference for the
  step timing (a clock the policy can see) is the usual tool; it adds an input the website does not have, so it
  is a question for a later session.

## `walk_g1_s1` (rung 1 + arm poses) against 0007

- **Predicted (65%): 400 or more pass, gait numbers within 15% of rung 1. Right.** 416 of 416, all green.
  Forward 0.116 m/s (rung 1: 0.118), 3.8 lift-offs per foot per second (3.6), tilt 4.2° (5.7°), no falls in training.

## Rung 2 in the website's simulator

`ladder2_s1` iteration 500, exported and run through the website's own reader and control loop: v0.5 model,
0.002 s steps, the page's uneven floor, 8 seeds per command, the same starts as the training evaluation.

- The reader matches the policy to 0.000002. 0 falls of 104. Every episode is green.
- Speeds, website against training: forward 0.115 against 0.117 m/s, backward 0.091 against 0.101, turn 0.98
  against 1.02 rad/s, curves and the diagonal within 9%.
- **Two commands still miss the plan's gate (parked share under 5%):** slow forward is parked 19% of the time
  (0.046 m/s at 0.06) and sideways-left 8% (0.057 m/s at 0.08). The tracking-only baseline missed on five (0006),
  with every episode red.
- A likely cause, not tested: the page's floor has mounds of 6 to 14 mm and ledges of 6 to 10 mm, and rung 2
  lifts its feet 8 mm. Training is on a flat floor; terrain is session 2 in the plan.

## The recipe so far

Rung 2: tracking, action change, a price on falling, leg torque. `l2_bounce_s1` and `l2_fidget_s1` are running;
either is added only if it improves on rung 2.
