# 0032 · No falls while the remote-control run learns, and a speed sweep (predictions)

26 November 2026, 16:04 UTC. Results of `remote_a`'s training-noise batch (predicted in 0029), and the
predictions for one more evaluation. Instance 62662296. Nothing is training.

## `remote_a`'s training-noise batch (iterations 0 to 800)

51 checkpoints, 37,536 episodes, no falls. 2.4 GB.

| Prediction of 0029 | How sure | Result |
|---|---|---|
| No episode falls in the whole batch. | 75% | Held: 0 of 37,536. |
| At every checkpoint up to iteration 100, under 10% of episodes pass. | 70% | Held: the most is 6.9%. |
| At iteration 800, under half of the episodes pass with training noise on. | 60% | Held: 0 of 736. |
| The batch is under 6 GB. | 70% | Held: 2.4 GB. |

All four held. With the three training-noise batches of today that is 83,616 episodes of early checkpoints
without one fall. The labels at 800 are `off_course` and `treadmill`: it steps and does not get anywhere.
`remote_a` learns later than the 0.8 mph runs (0031), so 0 to 800 shows only the not-walking part; the part
where its directions appear, about 1,200 to 3,600, has no training-noise batch.

## A speed sweep

The owner's question for a remote control is whether the speed can be chosen. The evaluations test 0.06,
0.12, 0.31 and 0.36 m/s forward and nothing between. New option `evaluate.py --sweep`: one straight-line
command per listed speed, 32 seeds, instead of the usual commands; batch `sweep`. It is an evaluation of
finished checkpoints, no training.

Speeds: 0.05, 0.09, 0.13, 0.18, 0.22, 0.27, 0.31, 0.36 and 0.40 m/s (0.1 to 0.9 mph), at iteration 6,000 of
`remote_a` (trained to 0.40 m/s) and of `production_fast_limit_a` (trained to 0.36 m/s; 0.40 is outside what
it was trained on).

| Prediction | How sure |
|---|---|
| `production_fast_limit_a` reaches every speed from 0.09 to 0.36 m/s within 5% (mean of 32). | 65% |
| `remote_a` reaches every speed from 0.09 to 0.36 m/s within 15%. | 60% |
| Told 0.40 m/s, `remote_a` reaches under 0.37 m/s. | 60% |
| Told 0.05 m/s, both move at half that speed or more on 28 or more of 32 seeds. | 50% |
| No episode falls in either sweep. | 90% |

Wrong would be: a gap between the slow and the fast commands where the walk does not follow the speed told
(for example two gaits with nothing between them). Then a remote control would have steps, not a dial.
