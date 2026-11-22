#!/usr/bin/env python3
"""Replay recorded motor targets in the training simulator (block B: do the simulators match?).

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/replay.py scripted.json --out replay_newton.json

The input is a recording of the website's scripted gait (50 Hz targets for the 15 motors). One
robot per recorded cell starts in the recording's first joint pose and is sent the same targets,
open loop, through the task's own action term. Compare with tools/compare_replays.py.
"""
import argparse
import contextlib
import json
import sys

import warp as wp

wp.config.enable_backward = False

import torch  # noqa: E402

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import resolve_task_config, setup_preset_cli  # noqa: E402

import scorbi_lab  # noqa: E402,F401
from scorbi_lab.robot import ARM_JOINTS, LEG_JOINTS  # noqa: E402

TASK = "Scorbi-Velocity-Flat"
parser = argparse.ArgumentParser()
parser.add_argument("recording")
parser.add_argument("--out", required=True)
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args

src = json.load(open(args.recording))
joints = src["meta"]["joints"]
cells = src["cells"]
N = len(cells)

env_cfg, _ = resolve_task_config(TASK, "rsl_rl_cfg_entry_point")
env_cfg.scene.num_envs = N
env_cfg.seed = 0
env_cfg.events.reset_base.params["pose_range"] = {}
env_cfg.events.reset_robot_joints.params["position_range"] = (0.0, 0.0)
env_cfg.terminations.base_contact = None
env_cfg.terminations.bad_orientation = None
env_cfg.episode_length_s = 1000.0

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    import gymnasium as gym

    env = gym.make(TASK, cfg=env_cfg)
    cleanup.callback(env.close)
    u = env.unwrapped
    device = u.device
    robot = u.scene["robot"]
    d = robot.data
    names = list(robot.joint_names)
    order = [names.index(j) for j in joints]  # the simulator's column for each recorded joint
    legs = [joints.index(j) for j in LEG_JOINTS]
    arm = [joints.index(j) for j in ARM_JOINTS]
    term = u.action_manager.get_term("joint_pos")
    assert [names[i] for i in term._joint_ids] == LEG_JOINTS

    ctrl = torch.tensor([c["ctrl"] for c in cells], dtype=torch.float32, device=device)  # cell, tick, joint
    q0 = torch.tensor([c["q"][0] for c in cells], dtype=torch.float32, device=device)
    default = d.default_joint_pos.torch.clone()
    default_legs = default[:, [names.index(j) for j in LEG_JOINTS]]

    env.reset()
    start = default.clone()
    start[:, order] = q0
    robot.write_joint_position_to_sim_index(position=start)
    robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(start))
    origin = u.scene.env_origins.clone()
    quat_xyzw = abs(d.default_root_pose.torch[0, 6].item()) > 0.5

    def state():
        quat = d.root_link_quat_w.torch
        if quat_xyzw:
            quat = quat[:, [3, 0, 1, 2]]
        return (d.root_link_pos_w.torch - origin).cpu().tolist(), quat.cpu().tolist(), d.joint_pos.torch[:, order].cpu().tolist()

    rec = [{"cell": c["cell"], "q": [], "torque": [], "pos": [], "quat": []} for c in cells]
    pos, quat, q = state()
    for i in range(N):
        rec[i]["pos"].append(pos[i]); rec[i]["quat"].append(quat[i]); rec[i]["q"].append(q[i])
    with torch.inference_mode():
        for t in range(ctrl.shape[1]):
            term.arm_target[:] = ctrl[:, t, arm]
            actions = (ctrl[:, t, legs] - default_legs) / term.cfg.scale
            env.step(actions)
            pos, quat, q = state()
            torque = robot.actuators.applied_effort.torch[:, order].cpu().tolist()
            for i in range(N):
                rec[i]["pos"].append(pos[i]); rec[i]["quat"].append(quat[i]); rec[i]["q"].append(q[i]); rec[i]["torque"].append(torque[i])
    with open(args.out, "w") as f:
        json.dump({"meta": {"what": f"the training simulator (Isaac Lab on Newton MuJoCo-Warp), flat floor, {u.cfg.sim.dt} s steps", "joints": joints, "rate_hz": 50,
                            "quat_order": "wxyz", "torque": "Isaac Lab's applied effort at each control step"}, "cells": rec}, f)
    print(f"{args.out}: {N} cells, {ctrl.shape[1]} control steps")
