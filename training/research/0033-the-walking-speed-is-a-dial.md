# 0033 · The walking speed is a dial

26 November 2026, 16:14 UTC. Results of the speed sweep predicted in 0032. Instance 62662296.

## The sweep (iteration 6,000, straight forward, 32 seeds a speed, batch `sweep`)

Every speed passes on 32 of 32 seeds in both runs, and no episode falls.

| Told | `production_fast_limit_a` reached | `remote_a` reached |
|---|---|---|
| 0.05 m/s (0.1 mph) | 0.048 m/s | 0.041 m/s |
| 0.09 m/s (0.2 mph) | 0.092 m/s | 0.082 m/s |
| 0.13 m/s (0.3 mph) | 0.133 m/s | 0.119 m/s |
| 0.18 m/s (0.4 mph) | 0.182 m/s | 0.163 m/s |
| 0.22 m/s (0.5 mph) | 0.222 m/s | 0.224 m/s |
| 0.27 m/s (0.6 mph) | 0.271 m/s | 0.282 m/s |
| 0.31 m/s (0.7 mph) | 0.311 m/s | 0.313 m/s |
| 0.36 m/s (0.8 mph) | 0.362 m/s | 0.340 m/s |
| 0.40 m/s (0.9 mph) | 0.402 m/s | 0.356 m/s |

- `production_fast_limit_a` is within 4% everywhere (worst at 0.05 m/s), mostly green on the motor check
  (25 to 30 green of 32), and its largest leg joint speed is 6.2 rad/s at 0.18 m/s, 7.1 at 0.27 and 8.1 at
  0.40 (4 seeds with full detail, after the first 5 s; servo 9.6).
- At 0.40 m/s (0.9 mph), the top of the range it was trained on (`FAST_FORWARD` is -0.12 to 0.40 m/s), it
  reaches 0.402 m/s and stays inside the servo's speed. One training seed, 32 starts. (0032 said 0.40 was
  outside its training range; that was wrong. 0.36 m/s is only the fastest command the evaluations test.)
- `remote_a` follows the same dial 18% short at 0.05 m/s, 9% short at 0.09 to 0.18, within 5% from 0.22 to
  0.31, and 6% and 11% short at 0.36 and 0.40. All amber from 0.22 up. Joint speeds 7.8, 8.3 and 9.2 rad/s at
  0.18, 0.27 and 0.40.
- Told 0.05 m/s, every one of the 32 seeds moves at 0.041 m/s or more in both runs: no standing still.

## Predictions of 0032

| Prediction | How sure | Result |
|---|---|---|
| `production_fast_limit_a` reaches every speed from 0.09 to 0.36 m/s within 5%. | 65% | Held: within 2.3%. |
| `remote_a` reaches every speed from 0.09 to 0.36 m/s within 15%. | 60% | Held: worst 9.4% (at 0.18). |
| Told 0.40 m/s, `remote_a` reaches under 0.37 m/s. | 60% | Held: 0.356. |
| Told 0.05 m/s, both move at half that speed or more on 28 or more of 32 seeds. | 50% | Held: 32 and 32. |
| No episode falls in either sweep. | 90% | Held. |

What 0032 called wrong (a gap between two gaits) is not there: the speed reached rises with the speed told
at every step of the sweep.

Over today's notes (0028 to 0033) 22 of 26 predictions held, most of them given at 50% to 70%. I have been
too unsure about these runs; the misses were about things I had not looked at (step length, stand height,
one joint speed, the turn giving way).

## What it means

- For walking forward, the 0.8 mph network is already a speed dial from 0.1 to 0.9 mph, its whole trained range.
- The remote-control run (every direction) holds the dial less exactly. Only forward was swept; backward,
  sideways and turning have two tested speeds each.
- Clip: `production_fast_limit_a/previews/strip_sweep_02_04_06_08mph_seed0_race.mp4` (four lanes, one start).
