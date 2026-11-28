# 0004 · First trained run (baseline, seed 1), the joint-limit fault behind the thrown robots, and the website test

22 November 2026, 06:20 UTC. GPU hours used so far: about 5.0, of which about 0.4 on recorded runs.

## Run `2026-11-22_05-56-23_baseline_s1`

Tracking-only reward (`track_twist_exp`, weight 1.5), 4,096 robots, seed 1, 500 iterations, code `b6077a6`.
Training took 317 s (155,000 steps a second with the larger contact limits; 164,000 before). 49,161
episodes, 273 simulated hours, 19 falls in training. The evaluation of all 39 checkpoints, the noise batch and the do-nothing control took about 7 minutes.

| Iteration | Passed of 416 | Forward at top command 0.12 | Turn left, command 1.0 | Action flip rate | Episodes red on the motor mark | Gait read from contacts | Fail labels |
|---|---|---|---|---|---|---|---|
| 0 | 64 (the stand commands) | 0.000 m/s | 0.00 rad/s | 0.00 | 0% | none | statue 352 |
| 30 | 64 | 0.000 | 0.00 | 0.21 | 0% | none | jackhammer 116, off_course 59, statue 177 |
| 50 | 81 | 0.011 | 0.07 | 0.31 | 87% | crawl | off_course 237, statue 43, jackhammer 35, treadmill 11, moonwalk 9 |
| 60 | 235 | 0.080 | 0.65 | 0.39 | 100% | other | off_course 147, jackhammer 33 |
| 100 | 354 | 0.129 | 0.93 | 0.34 | 100% | other | jackhammer 30, off_course 32 |
| 200 | 384 | 0.126 | 0.99 | 0.26 | 100% | trot | wander 28, jackhammer 4 |
| 300 | 416 | 0.122 | 0.95 | 0.20 | 100% | trot | none |
| 500 (final) | 414 | 0.116 | 0.92 | 0.15 | 100% | trot | wander 2 |

Do-nothing control through the same evaluation: 64 of 416 (the two stand commands), `statue` on the rest.
Its reward is 30.0 on stand, 15.8 on slow forward, 2.3 on top forward and 1.9 on turns; the policy earns 28 to 29 on every command.

### Against the predictions in 0003

| Prediction | Result |
|---|---|
| Walks forward and backward at half the commanded speed or more by 500 | **Right, and understated.** 97% of commanded speed forward and backward; every command passes in 32 of 32 seeds except stand (30). It walks by iteration 60. |
| Turning on the spot is worse than walking | **Wrong.** 0.92 and 0.99 rad/s against 1.0. |
| Jittery, flip rate over 20%, most episodes amber or red | **Right on the motors, close on jitter.** Every episode is red: a leg motor is at its 1.18 N·m limit for half the time (median). Flip rate 0.15 at the end, 0.39 at its worst. |
| Falls peak between iterations 5 and 100 | **Wrong. It almost never falls.** 19 falls in 49,161 training episodes, none in the evaluation at any checkpoint. |
| Curves lag straight walks (0002's worry about the joint term) | **Wrong.** Curves pass 32 of 32 by iteration 300, at the commanded speed and turn. The joint term stays. |

### What this means

- **The gait is not usable yet.** The feet lift off 8.7 times a second each: a buzzing shuffle on saturated
  motors, not steps. The real motors could not do it. This is what the reward ladder (block D) is for:
  action rate, torque, then foot air time.
- **Scorbi does not fall over on flat ground, and that matters for content.** The fails this run gives are
  `statue`, `jackhammer`, `treadmill`, `off_course` and a few `moonwalk`: funny to watch, but nobody goes
  down. Falls will have to come from shoves, from the exploration-noise batch, and later from stairs and getting up.
- **The standing commands fail in 2 of 32 seeds at the end** (`wander`: it drifts more than 0.10 m in 20 s).

## Why robots were thrown into the air

0003 found robots launched and lost with exploration noise, and raised the contact limits. That removed the
solver overflow but not the launches (4 of 416 were still lost afterwards). The cause was the joint limits.

- The same random leg targets in MuJoCo with `scorpion.xml`: 200 episodes, none thrown, no joint more than
  0.15 rad past its range.
- The model the training simulator actually steps, saved and run in MuJoCo: 2 of 200 lost.
- That model with one thing changed, joint limits as in `scorpion.xml`: 0 of 200 lost.

`scorpion.xml` leaves the joint-limit setting at MuJoCo's default (0.02 s, critically damped). The converter
does not carry a default, and Newton made up its own: 0.008 to 0.012 s with a damping ratio of 0.2. That is
stiffer than a 0.005 s step can hold, so a leg driven hard into its limit was thrown back with more energy
than it arrived with.

Two fixes, code `0831a54`:

- `tools/patch_usd_limits.py` writes MuJoCo's default onto all 15 joints of the converted model. Checked in the
  model the simulator steps. Run it after every conversion.
- Leg targets are clamped to the joint ranges in the action term, as the website clamps them.

After both: 832 noisy untrained episodes, none thrown or lost; oracle 169 checks, 0 problems.

**`baseline_s1` was trained before the fix.** It is kept and labelled as such. `baseline_v2_s1` repeats it on
the corrected model with the same seed, and is the baseline the other probes are compared with.

## The website test, done early (plan part 4, rule 1)

`baseline_s1` iteration 500, exported and run in the website's own simulator, headless: v0.5 model, 0.002 s
steps, the page's uneven floor. 2 seeds per command, 20 s.

| Command | Website simulator | Training simulator |
|---|---|---|
| Forward 0.12 m/s | 0.113 | 0.116 |
| Forward 0.06 m/s | **0.021, parked 42% of the time** | 0.064 |
| Backward 0.10 m/s | 0.096 | 0.097 |
| Sideways 0.08 m/s | 0.070 and 0.081 | 0.081 and 0.077 |
| Turn 1.0 rad/s | 0.95 and 0.92 | 0.92 and 0.99 |
| Curve 0.08 m/s with 0.5 rad/s | 0.077 with 0.46 | 0.086 with 0.50 |
| Falls | 0 of 26 | 0 of 416 |

- The reader gives the policy's own actions to within 0.000004. The page's control loop accepts the policy and
  walks 1.77 m in 20 s with the stick held forward.
- **The export path works and the two simulators agree,** except slow walking, which stalls on the page's
  bumps. Flat-ground training with no randomisation is the likely cause; the page's floor has mounds and ledges 6 to 14 mm high.
- Every episode is red on the motor mark there too.
