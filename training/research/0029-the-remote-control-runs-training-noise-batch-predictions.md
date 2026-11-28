# 0029 · The remote-control run's training-noise batch (predictions)

26 November 2026, 14:40 UTC. Instance 62662296. `remote_a` (0027) is at iteration 3,000 of 6,000.

## What is added

`remote_a` was started without a training-noise batch. Account 1's record for a skill asks for one (each
checkpoint rolled out with its own action noise), and this run is the footage for turning, walking backward
and walking sideways at speed. So after `remote_a` and its evaluation finish, one more evaluation runs:

`evaluate.py --iterations 0-800 --noise_std training --seeds 32 --detail_at all --skip_done`

23 commands, 32 seeds, about 51 checkpoints, about 37,500 episodes. It is an evaluation, not training: no
checkpoint changes. It waits for `/workspace/logs/remote_a.all_done` and writes `remote_a.noise_done`.

For scale: `production_fast_a`'s batch (39 checkpoints to iteration 500, 16 commands) was 19,968 episodes,
2.5 GB, 7 minutes of rollouts, and no episode fell.

## Predictions

| Prediction | How sure |
|---|---|
| No episode falls in the whole batch (`production_fast_a`: 0 of 19,968). | 75% |
| At every checkpoint up to iteration 100, under 10% of episodes pass (`production_fast_a`: 7% at 100). | 70% |
| At iteration 800, under half of the episodes pass with training noise on. | 60% |
| The batch is under 6 GB. | 70% |

Wrong would be: with every direction commanded fast, the noisy early checkpoints tip over, which would also
give request 7 (a tip with full detail) the footage that the shove ladder did not have (0028).

## Not started today

A second seed of `remote_a`, GET UP, stairs, ramp and blocks (requests 17 to 20). The copy to Drive goes at
about 2.5 MB/s and has about 20 GB to move before the instance ends at 19:00 UTC; another run's files would
not get out. The Supabase room left (about 80 MB under my 450 MB rule) would not hold its rows either.
