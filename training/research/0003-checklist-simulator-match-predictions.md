# 0003 · Checklist result, simulator match (block B), and predictions for the runs

22 November 2026, 05:55 UTC. Written before the first training run. GPU hours used so far: about 4.6, none on training.

## The checklist (plan part 3)

| Line | State | Evidence |
|---|---|---|
| Repositories cloned, v0.5 present | Done | Scorbi `41fbd3d`, 1,253 g |
| Secrets work | Done | vast.ai, Drive read and write. Supabase key present, not used. |
| Tables exist, a session row opens and closes | **Not done** | PR #31 is not applied. The owner said to keep working on everything that does not need the tables. Rows are backfilled from the files when it is. |
| Dry run to Google Drive, verified | Done | 19 files of the smoke run, sizes and hashes checked |
| Training model derived by script | Done | `tools/derive_training_model.py` (0001) |
| Joints mapped by name | Done | every tool looks joints up by name |
| Foot bodies survive, every body reports contacts | Done | oracle; foot forces add up to the weight (12.29 N of 12.29 N) |
| Oracle written and passes | Done | 169 checks, 0 problems (0002) |
| Website simulator runs headless under Node | Done | Node 24; Node 26 dropped the flag the site's own bake script uses |
| Dummy network exported with and without the normaliser is accepted by the website's parser | Done | largest difference from the policy's own answers: 7e-7 and 6e-8 |
| The dummy policy drives the robot 20 s in the website simulator; the per-command test gives numbers | Done | 26 episodes each, no falls, parked 100% as expected of a dummy |
| 13-command evaluation against the scripted gait | Done for the 8 commands the scripted gait has | table below; it has no sideways walk |
| Do-nothing arm through the same evaluation | Done | passes the two stand commands and nothing else |
| Recorder writes poses, numbers and fail labels | Done | tested on the untrained policy with and without noise and on do-nothing, not on the scripted gait |
| One clip rendered from recorded poses looks right | Done | re-rendered in the content look: cream floor, faint grid, soft shadow, no horizon |
| 16-robot smoke test | Done | on the GPU (0001) |
| Predictions for each planned run | Done | below |

Two things found on the website side:

- Isaac Lab's exporter writes the weights to a second file (`policy.onnx.data`). The website's reader
  refuses that. `tools/export.py` folds them back into one file and writes `policy.json` from the
  task's own settings.
- The website gate script must free MuJoCo's contact list after each read, or it runs out of memory
  within a few episodes.

## Block B: do the simulators match?

The website's scripted gait was driven like a player in the website's own simulator (v0.5 model,
the page's uneven floor). Its 50 Hz motor targets were then replayed, open loop, on a flat floor in
MuJoCo at 0.002 s and 0.005 s steps and in the training simulator at 0.005 s. 20 s each.

| Command | Simulator | Distance or turn | Leg tracking error (RMS) | Peak torque | Highest average torque |
|---|---|---|---|---|---|
| Forward | Website | 1.576 m | 1.61° | 0.69 N·m | 0.18 N·m |
| | MuJoCo 0.002 s | 1.601 m | 1.61° | 0.58 | 0.17 |
| | MuJoCo 0.005 s | 1.608 m | 1.48° | 0.61 | 0.19 |
| | Training 0.005 s | 1.609 m | 1.49° | 0.68 | 0.25 |
| Backward | Website | 1.896 m | 1.48° | 0.58 | 0.14 |
| | MuJoCo 0.002 s | 1.881 m | 1.49° | 0.47 | 0.15 |
| | Training 0.005 s | 1.858 m | 1.40° | 0.75 | 0.21 |
| Turn left | Website | 22.85 rad | 1.73° | 0.45 | 0.15 |
| | MuJoCo 0.002 s | 22.49 rad | 1.72° | 0.36 | 0.16 |
| | Training 0.005 s | 22.63 rad | 1.58° | 0.61 | 0.22 |

- **Body motion matches:** distance within 2%, turning within 1.5%, standing height 71.6 mm in both.
  The legs stay within 0.27° of the website's on average.
- **The 0.005 s step is fine:** MuJoCo at 0.005 s is within 1% of MuJoCo at 0.002 s.
- **Sideways drift does not match and is not expected to:** an open-loop replay drifts 0.05 to 0.27 m
  sideways over 1.6 m, differently in each simulator. A policy corrects this; a replay cannot.
- **Torque reads about 30% higher in the training simulator.** Not settled. The likely cause is when
  it is read: Isaac Lab reports the motor's effort right after a new target arrives, and the MuJoCo
  replay reads it at the end of the control step. The motor mark is therefore on the strict side.
  To settle it, compare the 100 Hz torque in a full-detail recording with MuJoCo's.

Full table: `simulator_match.json` beside the run folders in Drive.

## The evaluation, as built

- 13 commands × **32 seeds** (0 to 31) = 416 episodes at every saved checkpoint, 20 s each, about 8 s
  of GPU time per checkpoint. The plan said 8 seeds; Account 1's spec and the coordinator's queue say 32.
- **A fall does not end the episode.** It is timed with the task's rule (body touches the floor, or
  tilt past 60°) and the robot is recorded to 20 s, so the footage shows what happens after it.
  Numbers count up to the fall. In training a fall still ends the episode.
- Full detail at 100 Hz is recorded by running the 4 physics steps of a control step one by one.
  Checked: the motion is the same as in training to 0.000003 rad.
- Fail labels follow Account 1 part 8.9 with thresholds for Scorbi's size, plus three it needed:
  `tumble` (a fall none of the rules name), `treadmill` (legs working, body going nowhere) and
  `off_course` / `wander` (no fall, test not passed).
- **Account 1's pass tests cannot be met as written.** "5 body lengths in 10 s" is 0.15 m/s; the
  website's top speed is 0.12 m/s and the scripted gait reaches 0.078 m/s. The tests used here are:
  no fall, and 70% or more of the commanded speed on each commanded axis. The distance in 10 s and
  the turn in 6 s are saved for every episode, so Account 1's numbers can still be quoted.
- The shove is a step change in the body's speed (0.10 m/s, 0.125 N·s). **No ball is simulated.**

## Predictions (written before the runs)

All probes: 4,096 robots, 500 iterations, about 5 minutes each.

| Run | Prediction | How sure |
|---|---|---|
| Do-nothing control | Passes the two stand commands (64 of 416) and nothing else. Label: `statue`. | Seen on the untrained policy; 95% |
| Baseline, seed 1 (`track_twist_exp` only) | By iteration 500 it walks forward and backward at half the commanded speed or more. Turning on the spot is worse than walking. With no penalties the actions are jittery (flip rate over 20%) and most episodes are amber or red on the motor mark. Falls peak between iterations 5 and 100. | 70% that it walks at all |
| Baseline, seeds 2 and 3 | Same verdict as seed 1 on which commands pass. Speeds within 30% of each other. | 60% |
| Stock reward (two terms, 0.5 wide, uniform commands) | Training reward climbs to over 80% of its ceiling while the robot stands or shuffles: under 30% of the commanded speed on every moving command at iteration 500. This is the real cheat for Reward Hack. | 75% |
| Actor also sees its linear velocity | Tracks better at iteration 500, but by less than 20%. If so, the blind policy stays. | 55% |
| Curves against straight walks (cells 9, 10 against 2, 3) | Curves lag, because the joint term pays little until both parts are right (0002). | 65% |
| Reward ladder (block D) | An action-rate penalty halves the flip rate and costs under 20% of speed. A torque penalty moves most episodes to green. | 60% |
| Production run (block E) | All straight, sideways and stand commands pass in 29 of 32 seeds. Turning or curves may not. | 50% |
| Seeds B and C (block F) | Same commands pass as seed A. | 60% |
| What If: paid only for being tall | It stretches its legs and stands; it never walks. | 80% |

## Found while testing the recorder: the solver's contact limit was too small

06:05 UTC. With exploration noise on the untrained policy, 3 of 416 robots were thrown into the air
(0.07 m to 0.7 m in four control steps) and their state went to NaN. The log said
`nefc overflow - please increase njmax to 286`. The limits set in bring-up (`njmax` 100, `nconmax`
40) hold a standing robot, but not one with its body, arm and legs on the floor.

| `njmax` / `nconmax` | Robots thrown above 0.25 m | Robots that went to NaN | Wall time for 416 robots × 20 s |
|---|---|---|---|
| 100 / 40 | 3 | 3 | 10.4 s |
| 300 / 100 | 3 | 2 | 10.2 s |
| 600 / 200 | 0 | 0 | 9.7 s |

Now 800 / 250. This matters beyond footage: a NaN robot passes neither fall test (a comparison
with NaN is false), so in training it would never have been reset and would have fed NaN to PPO.

Three guards were added, none of which should ever fire:

- a `blow_up` termination in the task (state not a number, or body a metre up), logged as its own rate;
- `train.py` counts non-finite rewards per iteration (`non_finite_rewards_total`) and zeroes them;
- the evaluation marks such an episode `glitch`, holds its last good pose and never picks it.

The earlier throughput figure (164,000 steps a second) was measured at the small limits. Measure it again on the first run.
