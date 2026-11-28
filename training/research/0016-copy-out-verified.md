# 0016 · Copy-out verified

22 November 2026, 21:40 UTC. GPU hours used so far: about 20.3. Nothing is training and nothing is queued.

- All 23 recorded runs are on Drive under `Autonomous-Robotics/runs/walk/<run>/`. Every file was compared
  with the size and MD5 Drive reports as it was sent; no file mismatched.
- A count on three sides (`verify_copy.sh`, kept with the orb's scripts): for every run the orb holds every
  file the GPU holds, and the Drive record lists every file the orb holds, with matching total bytes. One
  record (`baseline_s1`) also lists the five simulator-check files stored beside it in `_checks/`.
- The four production runs and the What If have their final checkpoint's policy export on Drive; the four
  production exports have a website test result beside them (`export/<iteration>/site_gate.json`).
- Row files for all 23 runs are built against the PR #31 tables. Fourteen of them, the four long runs
  included, load into a local Postgres together: 613 MB of episode rows, so about 0.9 GB for the session.
  Nothing has been sent to the shared database.
- Not recorded: a full-detail (100 Hz) recording of a shove or ball hit at an earlier checkpoint. The 50 Hz
  poses of those episodes are there, and so are the checkpoints.
