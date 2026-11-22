#!/usr/bin/env python3
"""The per-command evaluation, which is also the footage (training plan, part 6).

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/evaluate.py \
        --run logs/rsl_rl/scorbi_flat/<run> --iteration 0 [--seeds 8] [--noise_std 1.0] [--do_nothing]

Rolls one checkpoint out on 13 fixed commands with the same seeds every time, for 20 s, with no
exploration noise unless --noise_std is given. Writes to <run>/scorbi/eval/<iteration>[_<batch>]/:

  poses.npz      50 Hz, one row per control step and robot: base position (x and y from the
                 robot's start, z above the floor), base orientation, the 15 joint angles in the model's order; and each
                 episode's length in steps. This is all a renderer needs.
  episodes.json  one entry per episode: cell, seed, command, fall and its time, speed achieved on
                 each axis, parked share, largest tilt, total reward and each reward term, each
                 joint's peak and average torque with the motor mark, and any shove.

A seed fixes the start (joint scatter) and the shove's direction. The same seed gives the same
start at every checkpoint. Iteration n is the policy after n updates; 0 is untrained.
"""
import argparse
import contextlib
import json
import math
import os
import sys
import time

import warp as wp

wp.config.enable_backward = False

import numpy as np  # noqa: E402
import torch  # noqa: E402

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper  # noqa: E402
from isaaclab_tasks.utils import resolve_task_config, setup_preset_cli  # noqa: E402

import scorbi_lab  # noqa: E402,F401
from scorbi_lab.robot import JOINTS, MOTOR  # noqa: E402

TASK = "Scorbi-Velocity-Flat"
SECONDS = 20.0
SHOVE_AT = 5.0
SHOVE_SPEED = 0.10  # m/s added to the base, sideways to a seeded direction
RATED_TORQUE = 0.36  # N m: the motor's everyday rating, 3.7 kg cm

# name, (forward m/s, sideways m/s, turn rad/s), shoved
CELLS = [
    ("stand", (0.0, 0.0, 0.0), False),
    ("forward_slow", (0.06, 0.0, 0.0), False),
    ("forward_top", (0.12, 0.0, 0.0), False),
    ("backward", (-0.10, 0.0, 0.0), False),
    ("sideways_left", (0.0, 0.08, 0.0), False),
    ("sideways_right", (0.0, -0.08, 0.0), False),
    ("turn_left", (0.0, 0.0, 1.0), False),
    ("turn_right", (0.0, 0.0, -1.0), False),
    ("curve_left", (0.08, 0.0, 0.5), False),
    ("curve_right", (0.08, 0.0, -0.5), False),
    ("diagonal", (0.07, 0.05, 0.0), False),
    ("forward_shoved", (0.08, 0.0, 0.0), True),
    ("stand_shoved", (0.0, 0.0, 0.0), True),
]

parser = argparse.ArgumentParser()
parser.add_argument("--run", required=True, help="the run's folder under logs/rsl_rl/scorbi_flat/")
parser.add_argument("--iteration", type=int, required=True)
parser.add_argument("--seeds", type=int, default=8, help="seeds per cell: 0 to seeds-1")
parser.add_argument("--noise_std", type=float, default=0.0, help="exploration noise on the actions; 0 = none")
parser.add_argument("--do_nothing", action="store_true", help="the control arm: zero actions instead of the policy")
parser.add_argument("--batch", default=None, help="folder suffix; default from the options")
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args

batch = args.batch or ("do_nothing" if args.do_nothing else "noise" if args.noise_std else "")
run = os.path.abspath(args.run)
out = os.path.join(run, "scorbi", "eval", str(args.iteration) + (f"_{batch}" if batch else ""))
os.makedirs(out, exist_ok=True)

N = len(CELLS) * args.seeds
STEPS = int(round(SECONDS / 0.02))

env_cfg, agent_cfg = resolve_task_config(TASK, "rsl_rl_cfg_entry_point")
env_cfg.scene.num_envs = N
env_cfg.seed = 0
env_cfg.observations.policy.enable_corruption = False
env_cfg.events.reset_base.params["pose_range"] = {}
env_cfg.events.reset_robot_joints.params["position_range"] = (0.0, 0.0)
env_cfg.commands.base_velocity.resampling_time_range = (1.0e6, 1.0e6)
env_cfg.commands.base_velocity.rel_standing_envs = 0.0

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    import gymnasium as gym
    from isaaclab_rl.entrypoints.backends.train_rsl_rl import check_rsl_rl_version, create_rsl_rl_runner, handle_deprecated_rsl_rl_cfg

    env = gym.make(TASK, cfg=env_cfg)
    cleanup.callback(env.close)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    u = env.unwrapped
    device = u.device
    robot = u.scene["robot"]
    d = robot.data
    names = list(robot.joint_names)
    order = [names.index(j) for j in JOINTS]

    checkpoint = os.path.join(run, "scorbi", f"ckpt_{args.iteration}.pt")
    policy = None
    if not args.do_nothing:
        # the same config clean-up the training entry point does before it builds the runner
        agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, check_rsl_rl_version())
        runner = create_rsl_rl_runner(env, agent_cfg)
        runner.load(checkpoint)
        policy = runner.get_inference_policy(device=device)

    # ── the same start for the same seed ─────────────────────────────────
    cell_of = np.repeat(np.arange(len(CELLS)), args.seeds)
    seed_of = np.tile(np.arange(args.seeds), len(CELLS))
    scatter = np.stack([np.random.default_rng(1000 + s).uniform(-0.05, 0.05, len(JOINTS)) for s in seed_of])
    shove_angle = np.array([np.random.default_rng(2000 + s).uniform(0, 2 * math.pi) for s in seed_of])
    commands = torch.tensor([CELLS[c][1] for c in cell_of], dtype=torch.float32, device=device)
    shoved = torch.tensor([CELLS[c][2] for c in cell_of], device=device)

    env.reset()
    start = d.default_joint_pos.torch.clone()
    start[:, order] += torch.tensor(scatter, dtype=torch.float32, device=device)
    limits = d.soft_joint_pos_limits.torch
    start = start.clamp(limits[..., 0], limits[..., 1])
    robot.write_joint_position_to_sim_index(position=start)
    robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(start))
    term = u.command_manager.get_term("base_velocity")
    term.vel_command_b[:] = commands
    term.is_standing_env[:] = False
    obs = env.get_observations()

    origin = u.scene.env_origins.clone()  # each robot's own patch of floor: z is then height above the floor
    identity = d.default_root_pose.torch[0, 3:7].tolist()
    quat_order = "xyzw" if abs(identity[3]) > 0.5 else "wxyz"

    root_pos = np.zeros((STEPS + 1, N, 3), np.float32)
    root_quat = np.zeros((STEPS + 1, N, 4), np.float32)
    joint_pos = np.zeros((STEPS + 1, N, len(JOINTS)), np.float32)

    def snapshot(t: int) -> None:
        root_pos[t] = (d.root_link_pos_w.torch - origin).cpu().numpy()
        root_quat[t] = d.root_link_quat_w.torch.cpu().numpy()
        joint_pos[t] = d.joint_pos.torch[:, order].cpu().numpy()

    alive = torch.ones(N, dtype=torch.bool, device=device)
    length = torch.full((N,), STEPS, device=device)
    fell = torch.zeros(N, dtype=torch.bool, device=device)
    measured = torch.zeros(N, device=device)  # steps counted for the speed numbers (after 1 s)
    vel_sum = torch.zeros(N, 3, device=device)
    parked = torch.zeros(N, device=device)
    tilt_max = torch.zeros(N, device=device)
    reward = torch.zeros(N, device=device)
    reward_terms = torch.zeros(N, len(u.reward_manager.active_terms), device=device)
    torque_peak = torch.zeros(N, len(JOINTS), device=device)
    torque_sum = torch.zeros(N, len(JOINTS), device=device)
    at_limit = torch.zeros(N, len(JOINTS), device=device)
    moving_axis = commands.abs() > 1e-6
    noise = torch.Generator(device=device).manual_seed(args.iteration * 7919 + 1)
    pushes: dict[int, dict] = {}
    began = time.time()

    snapshot(0)
    with torch.inference_mode():
        for t in range(1, STEPS + 1):
            actions = torch.zeros(N, 12, device=device) if policy is None else policy(obs)
            if args.noise_std:
                actions = actions + args.noise_std * torch.randn(actions.shape, generator=noise, device=device)
            if t == int(round(SHOVE_AT / 0.02)) + 1:
                vel = d.root_com_vel_w.torch.clone()
                kick = torch.tensor(np.stack([np.cos(shove_angle), np.sin(shove_angle)], 1) * SHOVE_SPEED, dtype=torch.float32, device=device)
                vel[:, :2] += kick * (shoved & alive)[:, None]
                robot.write_root_velocity_to_sim_index(root_velocity=vel)
                for i in torch.nonzero(shoved & alive).flatten().tolist():
                    pushes[i] = {"at_seconds": SHOVE_AT, "speed_change_m_s": SHOVE_SPEED, "direction": [float(np.cos(shove_angle[i])), float(np.sin(shove_angle[i])), 0.0],
                                 "impulse_newton_seconds": SHOVE_SPEED * scorbi_lab.robot.MODEL["mass"], "how": "a step change in the base's speed, in the world frame"}
            obs, rew, dones, extras = env.step(actions)
            term.vel_command_b[:] = commands
            done = dones.bool() & alive
            fall = done & ~extras["time_outs"].bool()
            # numbers for robots that were alive during this step
            a = alive.float()
            reward += rew * a
            reward_terms += u.reward_manager._step_reward * a[:, None]
            torque = robot.actuators.applied_effort.torch[:, order].abs()
            torque_peak = torch.maximum(torque_peak, torque * a[:, None])
            torque_sum += torque * a[:, None]
            at_limit += (torque > 0.98 * MOTOR["effort"]).float() * a[:, None]
            still = alive & ~done
            tilt = torch.acos((-d.projected_gravity_b.torch[:, 2]).clamp(-1, 1))
            tilt_max = torch.where(still, torch.maximum(tilt_max, tilt), tilt_max)
            if t > 50:
                v = torch.cat([d.root_link_lin_vel_b.torch[:, :2], d.root_link_ang_vel_b.torch[:, 2:3]], 1)
                vel_sum += v * still[:, None]
                measured += still
                progress = ((v * torch.sign(commands)) < 0.2 * commands.abs()) & moving_axis
                parked += (progress.any(dim=1) & still).float()
            fell |= fall
            length = torch.where(done, torch.full_like(length, t), length)
            alive &= ~done
            # a robot that fell has been reset by the environment: its pose is no longer recorded
            snapshot(t)
            if not alive.any():
                break

    length_np = length.cpu().numpy()
    for i in range(N):  # blank what was recorded after an episode ended
        root_pos[length_np[i]:, i] = np.nan
        root_quat[length_np[i]:, i] = np.nan
        joint_pos[length_np[i]:, i] = np.nan
    np.savez_compressed(os.path.join(out, "poses.npz"), root_pos=root_pos, root_quat=root_quat, joint_pos=joint_pos, length=length_np)

    steps = length.float().clamp(min=1)
    mean_torque = (torque_sum / steps[:, None]).cpu().numpy()
    peak = torque_peak.cpu().numpy()
    limit_share = (at_limit / steps[:, None]).cpu().numpy()
    achieved = (vel_sum / measured.clamp(min=1)[:, None]).cpu().numpy()
    term_names = list(u.reward_manager.active_terms)
    episodes = []
    for i in range(N):
        mark = "red" if limit_share[i].max() > 0.05 else "amber" if mean_torque[i].max() > RATED_TORQUE or peak[i].max() > 0.8 * MOTOR["effort"] else "green"
        episodes.append({
            "index": i,
            "cell": CELLS[cell_of[i]][0],
            "seed": int(seed_of[i]),
            "command": {"forward_m_s": CELLS[cell_of[i]][1][0], "sideways_m_s": CELLS[cell_of[i]][1][1], "turn_rad_s": CELLS[cell_of[i]][1][2]},
            "duration_seconds": float(length_np[i] * 0.02),
            "fell": bool(fell[i]),
            "fell_at_seconds": float(length_np[i] * 0.02) if fell[i] else None,
            "achieved": {"forward_m_s": float(achieved[i, 0]), "sideways_m_s": float(achieved[i, 1]), "turn_rad_s": float(achieved[i, 2])} if measured[i] > 0 else None,
            "parked_share": float(parked[i] / measured[i]) if measured[i] > 0 and moving_axis[i].any() else None,
            "largest_tilt_deg": math.degrees(float(tilt_max[i])),
            "distance_m": [float(x) for x in root_pos[max(length_np[i] - 1, 0), i, :2]],
            "reward": float(reward[i]),
            "reward_terms": {n: float(reward_terms[i, k]) for k, n in enumerate(term_names)},
            "motor_mark": mark,
            "torque_peak_n_m": {j: float(peak[i, k]) for k, j in enumerate(JOINTS)},
            "torque_mean_n_m": {j: float(mean_torque[i, k]) for k, j in enumerate(JOINTS)},
            "share_of_time_at_limit_max": float(limit_share[i].max()),
            "pushes": [pushes[i]] if i in pushes else [],
        })
    meta = {
        "task": TASK,
        "run": os.path.basename(run),
        "iteration": args.iteration,
        "batch": batch or "seeds",
        "checkpoint": None if args.do_nothing else os.path.basename(checkpoint),
        "noise_std": args.noise_std,
        "seeds_per_cell": args.seeds,
        "rate_hz": 50,
        "steps": STEPS,
        "joints": JOINTS,
        "quat_order": quat_order,
        "channels": {"root_pos": "metres; x and y from where the robot started, z above the floor", "root_quat": quat_order, "joint_pos": "radians, in the order of `joints`", "length": "steps recorded; rows from here on are NaN"},
        "start": "joint scatter of +-0.05 rad from rng(1000 + seed); shove direction from rng(2000 + seed)",
        "motor_mark": {"limit_n_m": MOTOR["effort"], "rated_n_m": RATED_TORQUE, "red": "a joint within 2% of the limit for over 5% of the episode", "amber": "average above rated, or peak over 80% of the limit"},
        "parked": "share of time, after the first second, moving at under 20% of a commanded speed",
        "wall_seconds": time.time() - began,
        "cells": [c[0] for c in CELLS],
    }
    with open(os.path.join(out, "episodes.json"), "w") as f:
        json.dump({"meta": meta, "episodes": episodes}, f, indent=1)

    print(f"\n{meta['batch']} · iteration {args.iteration} · {N} episodes · {meta['wall_seconds']:.1f} s · {out}")
    print(f"{'cell':16} {'falls':>5} {'fwd':>7} {'side':>7} {'turn':>7} {'parked':>7} {'tilt':>6} {'reward':>7}  marks")
    for c, (name, cmd, _) in enumerate(CELLS):
        rows = [e for e in episodes if e["cell"] == name]
        ach = [e["achieved"] for e in rows if e["achieved"]]
        mean = lambda k: sum(a[k] for a in ach) / len(ach) if ach else float("nan")  # noqa: E731
        park = [e["parked_share"] for e in rows if e["parked_share"] is not None]
        marks = {m: sum(e["motor_mark"] == m for e in rows) for m in ("green", "amber", "red")}
        print(f"{name:16} {sum(e['fell'] for e in rows):>5} {mean('forward_m_s'):>7.3f} {mean('sideways_m_s'):>7.3f} {mean('turn_rad_s'):>7.3f}"
              f" {(sum(park) / len(park) if park else float('nan')):>7.2f} {max(e['largest_tilt_deg'] for e in rows):>6.1f} {sum(e['reward'] for e in rows) / len(rows):>7.2f}  {marks}")
