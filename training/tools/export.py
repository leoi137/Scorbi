#!/usr/bin/env python3
"""Export a policy to ONNX with Isaac Lab's own exporter, with test vectors for the website's reader.

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/export.py --out <folder> \
        (--run logs/rsl_rl/scorbi_flat/<run> --iteration 500 | --random) [--no_normalizer]

Writes three files:
  policy.onnx   one file. The exporter puts the weights in a second file (policy.onnx.data), which
                the website's reader refuses, so they are folded back in here.
  policy.json   how the inputs and outputs line up with the robot, read from the task itself
                (the website's README, "Drop in a policy").
  vectors.json  8 random observations and the actions the policy itself gives for them, so the
                website's reader can be checked number for number.
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
# The website's own command limits, inside the trained range (plan 2.6 and 8.2).
SITE_LIMITS = {"lin_vel_x": [-0.12, 0.12], "lin_vel_y": [-0.08, 0.08], "ang_vel_z": [-1.0, 1.0]}
# Isaac Lab's observation functions, by the names the website's reader knows.
SITE_TERMS = {
    "base_lin_vel": "base_lin_vel", "base_ang_vel": "base_ang_vel", "projected_gravity": "projected_gravity",
    "generated_commands": "velocity_commands", "joint_pos_rel": "joint_pos_rel", "joint_vel_rel": "joint_vel_rel",
    "last_action": "last_action",
}
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
    import onnx

    onnx_path = os.path.join(args.out, "policy.onnx")
    model = onnx.load(onnx_path)  # reads the weights from policy.onnx.data
    onnx.save(model, onnx_path, save_as_external_data=False)
    if os.path.exists(onnx_path + ".data"):
        os.remove(onnx_path + ".data")
    onnx.checker.check_model(onnx.load(onnx_path))
    policy = runner.get_inference_policy(device=env.unwrapped.device)
    obs = env.get_observations()
    x = torch.randn_like(obs["policy"]) * 2.0
    obs["policy"] = x
    with torch.inference_mode():
        y = policy(obs)
    u = env.unwrapped
    robot = u.scene["robot"]
    names = list(robot.joint_names)
    term = u.action_manager.get_term("joint_pos")
    action_joints = [names[i] for i in term._joint_ids]
    for limit, trained in zip(SITE_LIMITS.values(), (u.cfg.commands.base_velocity.ranges.lin_vel_x, u.cfg.commands.base_velocity.ranges.lin_vel_y, u.cfg.commands.base_velocity.ranges.ang_vel_z)):
        assert trained[0] <= limit[0] and limit[1] <= trained[1], f"the website's limit {limit} is outside the trained range {trained}"
    observations = []
    for name, cfg in zip(u.observation_manager.active_terms["policy"], u.observation_manager._group_obs_term_cfgs["policy"]):
        site = SITE_TERMS[cfg.func.__name__]
        assert cfg.clip is None, f"{name} is clipped, which the website does not do"
        observations.append(site if cfg.scale in (None, 1.0) else {"name": site, "scale": float(cfg.scale)})
    default = robot.data.default_joint_pos.torch[0].tolist()
    with open(os.path.join(args.out, "policy.json"), "w") as f:
        json.dump({
            "about": "Written by training/tools/export.py in the Scorbi repository from the task's own settings.",
            "onnx": "policy.onnx",
            "action_joints": action_joints,
            "observation_joints": names,
            "default_joint_pos": {n: round(v, 6) for n, v in zip(names, default)},
            "action_scale": float(term.cfg.scale),
            **({"clip_actions": float(agent_cfg.clip_actions)} if agent_cfg.clip_actions is not None else {}),
            "observations": observations,
            "control_dt": round(u.cfg.sim.dt * u.cfg.decimation, 6),
            "command_limits": SITE_LIMITS,
            "heading_stiffness": 0.5,
        }, f, indent=2)
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
