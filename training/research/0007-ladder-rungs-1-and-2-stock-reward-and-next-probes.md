# 0007 · Rungs 1 and 2, the stock reward, and predictions for the long-steps and disturbance probes

22 November 2026, 07:36 UTC. GPU hours used so far: about 6.2. Written before `ladder1_steps_s1` and the
`walk_g*` runs start; rungs 3 to 6 and the linear-velocity probe are still running.

## Correction to 0006: baseline seed 3

0006 left seed 3's row unfilled. `baseline_v2_s3`, final checkpoint: 416 of 416 passed, 90% first passed at
iteration 140, forward 0.118 m/s at 0.12, turn 0.97 rad/s at 1.0, action flip rate 0.24, 100% red, 7.4
lift-offs per foot per second.

## Rungs 1 and 2 against 0005

Final checkpoint (500), 13 commands × 32 seeds. `summarize.py` now also prints how long a swing lasts.

| Run | Passed | Flip rate | Red / green | Highest mean motor torque | Lift-offs per foot per second | Swing time | Swing lift | Largest tilt | Stand drift |
|---|---|---|---|---|---|---|---|---|---|
| `baseline_v2_s1` (tracking only) | 416 | 0.17 | 100% / 0% | 0.91 N·m | 8.2 | 0.06 s | 6.9 mm | 3.9° | 11 mm |
| `ladder1_s1` (+ `action_rate`, + `fell`) | 416 | 0.10 | 0% / 100% | 0.22 | 3.6 | 0.10 s | 8.7 mm | 5.7° | 9 mm |
| `ladder2_s1` (+ `leg_torque`) | 416 | 0.09 | 0% / 100% | 0.18 | 3.5 | 0.12 s (iteration 400) | 8.7 mm (iteration 400) | 3.6° | 8 mm |

- **Rung 1.** Predicted: flip rate under 0.08, 390 or more pass, under 5 lift-offs a second, still mostly red.
  The flip rate is 0.10 (wrong), 416 pass (right), 3.6 lift-offs (right), and no episode is red (wrong: the
  one penalty also took every motor off its limit; mean torque fell to a quarter).
- **Rung 2.** Predicted: under half red, speeds down by under 15%. Both hold, but rung 1 had already done it.
  The torque penalty itself moves little: torque 0.22 to 0.18 N·m, tilt 5.7° to 3.6°. Speeds are unchanged.
- Rung 2's swing time and lift are from iteration 400: the final checkpoint's recording had not been copied
  off the GPU when this was written. The next entry has them.
- Neither rung fell in training (0 and 0 falls in 49,152 episodes each).
- **The look is not there yet.** Rung 1 at 0.12 m/s swings each foot for 0.10 s, 3.6 times a second: a stride of
  3 cm. In the follow-camera clip a viewer (and the video model asked to judge it) sees a robot that shuffles
  on the spot, although it covers 0.95 m in 8 s. The side-view frames show real lift-offs. The website's
  scripted gait swings for 0.2 s.
- A second cause of "it looks parked": the follow camera on a cream floor with a faint grid gives the eye
  nothing to measure motion against. That is a render question for the account orbs (a fixed camera, or a
  stronger grid), not a training one.

## The stock reward against 0003

`stock_reward_s1`: Isaac Lab's two stock tracking terms, 0.5 wide, with its uniform command sampler.

- **Predicted (75%): reward over 80% of its ceiling while the robot stands or shuffles, under 30% of the
  commanded speed on every moving command.** The first half is right, the second is wrong.
- The reward reaches 29.45 of 30 in training and 29.75 to 29.92 of 30 on every evaluation command: 99%.
- The robot does walk: 0.102 m/s at 0.12, turns at 0.98 rad/s. But it passes 225 of 416. It walks at 0.037 m/s
  when told 0.06, drifts 33 cm in 20 s when told to stand (`wander`, 32 of 32), and fails backward, sideways
  left and both shoved commands (`off_course`).
- Its pass count goes up and down with training: 318 at iteration 80, 153 at 200, 299 at 400, 225 at 500.
  The reward cannot tell these apart. All episodes are red on the motor mark.
- So the stock reward's failure on Scorbi is not a statue. It is a reward that reads 99% for a robot that fails
  46% of its tests. For "Reward Hack" content the pair is `stock_reward_s1` against `baseline_v2_s1`.

## Probe: long steps (`ladder1_steps_s1`)

- **One change from rung 1:** `+ long_steps`, weight 25. At each touchdown it pays for how much longer than 0.1 s
  the foot was in the air, capped at 0.2 s; a shorter swing costs; nothing when told to stand.
- **Price.** The reward manager multiplies by the 0.02 s step, so 25 is 0.5 per second of swing beyond 0.1 s.
  The scripted gait (two 0.2 s swings a second per foot) would earn 0.4 a second; rung 1's patter earns
  about nothing. Tracking pays 1.5 a second.
- **Why not the existing `step_time`.** It pays for total time in the air, so many short swings earn the same as
  few long ones.
- **Known risk.** Marching on the spot with long swings earns 0.4. When told 0.06 m/s, standing still already
  earns 0.79, so marching on the spot gets 1.19 against 1.5 for walking with a patter and 1.9 for walking with
  long steps. Walking should still win; slow turns (0.3 rad/s) are closer: 1.57 against 1.5.

| Prediction | How sure |
|---|---|
| Swing time on forward 0.12 m/s rises from 0.10 s to 0.15 s or more; lift-offs per foot fall under 3 a second. | 60% |
| Still passes 400 or more of 416, still green. | 65% |
| Parked share on slow forward stays under 5%. If it marches on the spot there, the weight is too high. | 60% |

Wrong would be: swing time unchanged (the term is too weak or badly formed), or the pass count under 375.

## Probes: disturbances, one group at a time (`walk_g1_s1` to `walk_g8_s1`)

Code: `scorbi_lab/production.py` and the action term in `scorbi_lab/actions.py`. Task
`Scorbi-Velocity-Flat-Walk-G<n>` has the first n groups on. `tools/check_disturbances.py` confirms each group
acts (on G8) and that G0 is the plain robot. The reward is rung 1's while block D is undecided; the evaluation
always runs the nominal robot with no disturbances, so runs stay comparable.

| n | Group | What training gets | Against the plan's proposal |
|---|---|---|---|
| 1 | Arm | Starts in one of the website's four arm poses (rest, wave, grab, carry), moves to another about every 8 s. 0 to 8 g added to the claw's finger. | Every robot carries 0 to 8 g, not "some carry 8 g". |
| 2 | Hand-off | About every 15 s a script takes the legs to a pose near the stance for 0.5 to 2 s. Meanwhile the policy is told to stand and its last action is set from the measured joint angles. | As proposed. |
| 3 | Shoves | 0.2 to 1.0 m/s, any direction, every 4 to 8 s. | The plan's 0.05 to 0.1 m/s does nothing to Scorbi (0006). |
| 4 | Friction | Each foot 0.5 to 1.3 (the model's is 1.1). | One coefficient per shape on this backend, so static and dynamic are one number. |
| 5 | Mass | -50 to +150 g on the body. | The centre of mass is not shifted: Isaac Lab warns that it can make this backend unstable. |
| 6 | Motors | Gains × 0.75 to 1.25, torque limit × 0.8 to 1.2, zero offset up to 0.02 rad. | As proposed. |
| 7 | Delay | 0, 1 or 2 control steps. | As proposed. |
| 8 | Resets | Joint scatter 0.10 rad; start speeds up to 0.05 m/s and 0.3 rad/s. | As proposed. |

Checked on 512 robots holding their stance for 20 s with all eight groups on: no falls, no lost robots, masses
1,205 to 1,409 g, torque limits 0.94 to 1.42 N·m, 0.9 hand-offs per 15 robot-seconds.
**Not checked:** that the changed torque limit and friction reach the solver. Both read back changed; neither
was tested by its effect on motion.

| Run | Prediction | How sure |
|---|---|---|
| G1, G2 | Pass 400 or more of 416; gait numbers within 15% of rung 1. | 65% |
| G3 (shoves) | Falls at the 1.5 m/s shove drop from 23 and 21 of 32 (baseline) to under 12 each. More feet on the floor: share of time with three or more feet down rises above rung 2's 0.35. Still 390 or more pass. | 55% |
| G4, G5 | No visible change. | 65% |
| G6, G7 | The first groups that may cost passes at 500 iterations; delay raises the flip rate. Still 375 or more. | 50% |
| G8 (everything) | 375 or more of 416 at iteration 500, no red. | 50% |

Wrong would be: a group that drops the pass count under 300 (it is then re-sized or left out of the long run),
or shoves in training that do not reduce falls at the shove ladder.
