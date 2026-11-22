#!/usr/bin/env python3
"""Export a policy to ONNX with Isaac Lab's own exporter, with test vectors for the website's reader.

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/export.py --out <folder> \
        (--run logs/rsl_rl/scorbi_flat/<run> --iteration 500 | --random) [--no_normalizer]

Writes policy.onnx and vectors.json: 8 random observations and the actions the policy itself gives
for them, so a reader on the website's side can be checked number for number.
"""
import argparse
import contextlib
import json
import os
import sys

import warp as wp

wp.config.enable_backward = False

import torch  # noqa: E402

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper  # noqa: E402
from isaaclab_tasks.utils import resolve_task_config, setup_preset_cli  # noqa: E402

import scorbi_lab  # noqa: E402,F401

TASK = "Scorbi-Velocity-Flat"
parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--run", default=None)
parser.add_argument("--iteration", type=int, default=None)
parser.add_argument("--random", action="store_true", help="random weights, no checkpoint")
parser.add_argument("--no_normalizer", action="store_true")
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args
assert args.random != (args.run is not None and args.iteration is not None), "give --random, or --run and --iteration"

env_cfg, agent_cfg = resolve_task_config(TASK, "rsl_rl_cfg_entry_point")
env_cfg.scene.num_envs = 8
if args.no_normalizer:
    agent_cfg.actor.obs_normalization = False
    agent_cfg.critic.obs_normalization = False

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    import gymnasium as gym
    from isaaclab_rl.entrypoints.backends.train_rsl_rl import check_rsl_rl_version, create_rsl_rl_runner, handle_deprecated_rsl_rl_cfg

    env = gym.make(TASK, cfg=env_cfg)
    cleanup.callback(env.close)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, check_rsl_rl_version())
    torch.manual_seed(7)
    runner = create_rsl_rl_runner(env, agent_cfg)
    if not args.random:
        runner.load(os.path.join(os.path.abspath(args.run), "scorbi", f"ckpt_{args.iteration}.pt"))
    os.makedirs(args.out, exist_ok=True)
    runner.export_policy_to_onnx(path=args.out, filename="policy.onnx")
    policy = runner.get_inference_policy(device=env.unwrapped.device)
    obs = env.get_observations()
    x = torch.randn_like(obs["policy"]) * 2.0
    obs["policy"] = x
    with torch.inference_mode():
        y = policy(obs)
    u = env.unwrapped
    with open(os.path.join(args.out, "vectors.json"), "w") as f:
        json.dump({
            "source": "random weights" if args.random else f"{os.path.basename(os.path.abspath(args.run))} iteration {args.iteration}",
            "normalizer": not args.no_normalizer,
            "observation_terms": list(u.observation_manager.active_terms["policy"]),
            "observation_dims": [list(d) for d in u.observation_manager.group_obs_term_dim["policy"]],
            "obs": x.tolist(),
            "actions": y.tolist(),
        }, f)
    print(f"exported to {args.out}: {os.path.getsize(os.path.join(args.out, 'policy.onnx'))} bytes, {x.shape[1]} inputs, {y.shape[1]} outputs")
