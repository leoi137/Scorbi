# 0028 · One network walks slow and fast, inside the servo's speed (the probe)

26 November 2026, 14:20 UTC. Results of `remote_probe_s1` (0026). Instance 62662296.
`production_fast_limit_a` (0025) and `remote_a` (0027) are still training; their results come in later notes.

## `remote_probe_s1`, iteration 1,500

736 of 736 pass (23 commands, 32 seeds), no falls, gait trot. Checkpoint hash `c99c380ef5e19fcb`.
One seed, no disturbances in training, flat ground.

| Command | Told | Reached | Passed | Largest leg joint speed (limit 9.6 rad/s) |
|---|---|---|---|---|
| forward slow | 0.06 m/s | 0.058 m/s | 32 | 5.2 rad/s |
| forward 0.8 mph | 0.36 m/s | 0.360 m/s | 32 | 9.0 rad/s |
| backward 0.7 mph | 0.31 m/s | 0.309 m/s | 32 | 8.4 rad/s |
| sideways left / right 0.5 mph | 0.22 m/s | 0.216 / 0.207 m/s | 32 / 32 | 8.0 / 8.6 rad/s |
| turn left / right | 2.0 rad/s (115°/s) | 2.00 / 2.03 rad/s | 32 / 32 | 8.8 / 8.3 rad/s |
| forward with a turn | 0.31 m/s, 1.5 rad/s | 0.306 m/s, 1.47 rad/s | 32 | 9.4 rad/s |
| diagonal | 0.25 m/s, 0.15 m/s | 0.243 m/s, 0.150 m/s | 32 | 8.3 rad/s |

- No leg joint is over 9.6 rad/s at any sample of the nine commands checked (`joint_speed.py`, the 4 seeds of
  each command that have full detail, after the first 5 s). `all_fast_s1` was over it up to 16% of the time.
- The torque limit (1.17 N·m or more) is touched most on the fast left turn: 1.8% of joint samples.
- The slow walk is back: `forward_slow` passes 32 of 32 (`all_fast_s1`: 11). During training it passed 0 of 32
  at iterations 200 and 300, 31 at 400, and 32 at 500, 750, 1,000 and 1,500.
- Every command passes for the first time at iteration 425 (736 of 736); at 500 it is 733, and it is 736 at
  750, 950, 1,000, 1,300, 1,400 and 1,500.

So the two changes of 0026 do what they were made for: the narrow draws for 40% of the robots keep the slow
commands, and the price on leg speed keeps the fast ones inside the servo.

## Predictions of 0026

| Prediction for iteration 1,500 | How sure | Result |
|---|---|---|
| Passes `forward_slow` on 28 or more of 32. | 65% | Held: 32. |
| Passes all 32 seeds of each of the 13 usual commands. | 45% | Held. |
| Passes every one of the ten faster commands on 24 or more of 32. | 55% | Held: 32 on each. |
| No command has a leg joint over 9.6 rad/s for more than 2% of the time. | 55% | Held: 0% on the nine checked. |
| Turning at 2.0 rad/s is the command that gives way: under 1.8 rad/s reached on one side. | 40% | Wrong: 2.00 and 2.03. |

Four of five held, and each was given at 65% or less: I was too unsure about a change whose early look at
iteration 1,000 (0027) had already passed.

## Not shown by this

- It is one seed without disturbances. `remote_a` (0027) is the run with the eight disturbance groups and
  the wider commands (0.9 mph forward and backward, 0.67 mph sideways, 2.5 rad/s).
- The joint-speed check reads 4 seeds a command, not 32.
- Slow sideways, slow backward and slow turns are in the 13 usual commands and pass; nothing between the slow
  and the fast commands is tested (for example 0.2 m/s forward).

## Also today

- `tip_find.py` (kept in the orb's backup folder and on the GPU in `/workspace/export/`) looked for a fall
  where the point under the body leaves the polygon of the feet on the floor (request 7). In the 51 falls with
  full detail of `production_a`'s shove ladder at iterations 0, 50, 100 and 200 there is none: all four feet
  are down until the shove, then the feet leave the floor within one sample. A shove is not a tip.
- `drive_sync.py stream`: the upload's socket timeout goes from 1,800 s to 180 s. A stream hung for 23 minutes
  on a dead ssh pipe after the orb had slept.
