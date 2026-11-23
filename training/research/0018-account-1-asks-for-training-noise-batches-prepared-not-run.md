# 0018 · Account 1 asks for batches with training noise: prepared, not run

23 November 2026. The instance is stopped (0017), so nothing in this entry has run.

## The request and what was checked

Account 1's readiness check fails on the four production runs: in the noise-free batches every walking
command goes from `statue` to passing between two checkpoints, so there is one fail label and no "almost".

- Checked: the noise batches of every recorded run exist only at the first and last checkpoint, with a fixed
  noise of 1.0 and 8 seeds per command (`run_recorded.sh`).
- Checked: `iterations.jsonl` has the noise training used after each update (`extras.action_std`). For
  `production_a`: 0.99 at iteration 1, 0.56 at 50, 0.36 at 100, 0.22 at 200, 0.13 at 375. Iteration 0 has no
  logged value; the agent starts at 1.0 (`params/agent.yaml`).

## What is prepared

- `evaluate.py --noise_std training`: each checkpoint is rolled out with its own training noise. The batch is
  named `training_noise` (folders `<iteration>_training_noise`), so the older fixed-noise folders are not
  overwritten. `--iterations 0-400` picks every saved checkpoint in a range.
- The noise is one number for all twelve leg joints (the mean training logged), not the per-joint values.
- `rows.py` stores the new batch as `noise` with the tag `training_noise`. The table allows one `noise` batch
  per checkpoint, so at iteration 0 the new batch (same noise of 1.0, 32 seeds) replaces the old one in the
  rows; the old files stay in Drive.
- Tested on the orb with `production_a`'s files: the range gives 35 checkpoints for 0 to 400, and the noise
  values read back as above. The rollout itself needs Isaac Lab and is untested.
- The queue (`noise_a1.sh`, with the orb's scripts): 0 to 400 for `production_a`, 0 to 375 for
  `production_plain_a`, 0 to 475 for `production_b`, 0 to 300 for `production_fidget_a`: each run up to its
  first checkpoint where all 416 noise-free episodes pass. 137 batches, 32 seeds per command, full detail for
  the picked moments at every checkpoint. About 1 GPU hour and 8 GB.

## A difference from training that the batches will not close

Training's success rate (17% at iteration 200, 55% at 300) was measured with all eight disturbance groups on
and commands that change. These batches add the noise only. If the "almost" in training came from the
disturbances, the noise batches will still jump.

| Prediction | How sure |
|---|---|
| For `production_a`, forward at top speed passes between 4 and 28 of 32 seeds at two or more checkpoints (noise-free: none). | 60% |
| Across 0 to 400 the walking commands show three or more fail labels besides `statue`. | 70% |
