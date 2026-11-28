#!/usr/bin/env python3
"""Run a Scorbi task with zero actions (the do-nothing control) or random actions.

    uv run python /workspace/Scorbi/training/tools/zero_agent.py --task Scorbi-Velocity-Flat --num_envs 16 --max_steps 500
    ... --random   for uniform random actions

Isaac Lab's own zero_agent.py does not load tasks from installed projects, so this registers
Scorbi's first.
"""
import sys

import warp as wp

wp.config.enable_backward = False

import scorbi_lab  # noqa: E402,F401  registers the tasks
from isaaclab_rl.entrypoints import run_random_agent_cli, run_zero_agent_cli  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--random" in argv:
        argv.remove("--random")
        raise SystemExit(run_random_agent_cli(argv))
    raise SystemExit(run_zero_agent_cli(argv))
