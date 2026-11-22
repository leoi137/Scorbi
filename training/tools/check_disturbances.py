#!/usr/bin/env python3
"""Check that a production task's disturbances do what production.py says (training plan, part 5.5).

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/check_disturbances.py --task Scorbi-Velocity-Flat-Walk-G8

Steps the task for 20 s with zero actions (a robot that holds its stance) and prints what each
group changed: masses, foot friction, servo gains and strength, delay, zero offset, hand-offs, arm
poses, shoves, and how many robots fell. Exits 1 if a group that is on left no trace, or if any
state is not a number.
"""
import argparse
import contextlib
import sys

import warp as wp

wp.config.enable_backward = False

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import resolve_task_config, setup_preset_cli  # noqa: E402

import scorbi_lab  # noqa: E402,F401
from scorbi_lab.production import GROUPS  # noqa: E402
from scorbi_lab.robot import MODEL, MOTOR  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--task", default="Scorbi-Velocity-Flat-Walk-G8")
parser.add_argument("--num_envs", type=int, default=512)
parser.add_argument("--seconds", type=float, default=20.0)
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args

problems: list[str] = []


def check(ok: bool, what: str) -> None:
    if not ok:
        problems.append(what)
        print("PROBLEM:", what)


def span(t: torch.Tensor) -> str:
    return f"{t.min().item():.4f} to {t.max().item():.4f}"


env_cfg, _ = resolve_task_config(args.task, "")
env_cfg.scene.num_envs = args.num_envs
on = GROUPS[: env_cfg.disturbances]
print("task", args.task, "groups on:", on)

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    env = gym.make(args.task, cfg=env_cfg)
    cleanup.callback(env.close)
    u = env.unwrapped
    robot = u.scene["robot"]
    d = robot.data
    term = u.action_manager.get_term("joint_pos")
    command = u.command_manager.get_term("base_velocity")
    env.reset()
    n = u.num_envs
    bodies, joints = list(robot.body_names), list(robot.joint_names)

    # ── what startup changed ─────────────────────────────────────────────
    mass = d.body_mass.torch
    total = mass.sum(dim=1)
    base, finger = mass[:, bodies.index("base")], mass[:, bodies.index("finger")]
    print(f"total mass g: {span(total * 1000)} (model {MODEL['mass'] * 1000:.1f}); base g: {span(base * 1000)}; finger g: {span(finger * 1000)}")
    check(("arm" in on) == bool(finger.max() - finger.min() > 0.004), "the block in the claw: finger mass spread is wrong for this task")
    check(("mass" in on) == bool(base.max() - base.min() > 0.1), "added mass: base mass spread is wrong for this task")
    kp, kd, effort = d.joint_stiffness.torch, d.joint_damping.torch, d.joint_effort_limits.torch
    print(f"stiffness: {span(kp)} (model {MOTOR['kp']}); damping: {span(kd)}; torque limit: {span(effort)} (model {MOTOR['effort']})")
    check(("motors" in on) == bool(kp.max() / kp.min() > 1.3), "motor gains: stiffness spread is wrong for this task")
    check(("motors" in on) == bool(effort.max() / effort.min() > 1.2), "motor strength: torque limit spread is wrong for this task")
    try:
        model = u.sim.physics_manager.get_model()
        mu = wp.to_torch(robot._root_view.get_attribute("shape_material_mu", model)[:, 0])
        distinct = torch.unique(mu.flatten()).numel()
        print(f"friction over {mu.shape[1]} shapes: {span(mu)}, {distinct} distinct values")
        check(("friction" in on) == (distinct > 20), "foot friction: spread is wrong for this task")
    except Exception as e:  # noqa: BLE001  reading it back is this backend's private path
        print("friction could not be read back:", repr(e))
    print(f"delay steps: {[int((term._delay == k).sum()) for k in range(term.cfg.delay_steps + 1)]}; zero offset rad: {span(term._zero)}")
    check(("delay" in on) == bool(term._delay.max() > 0), "delay is wrong for this task")
    check(("motors" in on) == bool(term._zero.abs().max() > 0.01), "zero offset is wrong for this task")

    # ── 20 s holding the stance ──────────────────────────────────────────
    steps = int(round(args.seconds / u.step_dt))
    zero = torch.zeros(n, term.action_dim, device=u.device)
    scripted_steps = torch.zeros(n, device=u.device)
    started = 0
    was = torch.zeros(n, dtype=torch.bool, device=u.device)
    falls = timeouts = 0
    arm_seen: set = set()
    arm_moved = torch.zeros(n, dtype=torch.bool, device=u.device)
    first_arm = term.arm_target.clone()
    biggest_jump = 0.0
    worst_last = worst_cmd = 0.0
    speed_before = d.root_lin_vel_w.torch[:, :2].clone()
    with torch.inference_mode():
        for t in range(steps):
            before = (d.joint_pos.torch[:, term._joint_ids] - term._stance) / term._scale  # what the hand-off reads
            obs, _, terminated, truncated, _ = env.step(zero)
            now = term.scripted
            started += int((now & ~was).sum())
            scripted_steps += now
            if now.any():
                # the policy's inputs while a script holds the legs: told to stand, last action from the joints
                policy = obs["policy"] if isinstance(obs, dict) else obs
                held = now & was & ~(terminated | truncated)  # held through the whole step
                if held.any():
                    worst_cmd = max(worst_cmd, policy[held, 6:9].abs().max().item())
                    worst_last = max(worst_last, (policy[held, -12:] - before[held]).abs().max().item())
            was = now.clone()
            falls += int(terminated.sum())
            timeouts += int(truncated.sum())
            arm_moved |= (term.arm_target - first_arm).abs().amax(dim=1) > 0.05
            for row in term._arm_goal[:: max(1, n // 64)].round(decimals=2).tolist():
                arm_seen.add(tuple(row))
            speed = d.root_lin_vel_w.torch[:, :2]
            jump = (speed - speed_before).norm(dim=1)
            jump[terminated | truncated] = 0.0
            biggest_jump = max(biggest_jump, jump.max().item())
            speed_before = speed.clone()
            check(bool(torch.isfinite(d.root_link_pos_w.torch).all()) and bool(torch.isfinite(d.joint_pos.torch).all()), f"a state is not a number at step {t}")
            if problems and "not a number" in problems[-1]:
                break
    robot_seconds = n * args.seconds
    print(f"hand-offs started: {started} ({started / robot_seconds * 15:.2f} per 15 robot-seconds); share of time scripted: {scripted_steps.sum().item() / (n * steps):.3f}")
    print(f"while scripted: largest command seen by the policy {worst_cmd:.4f}; largest gap between its last action and the joints {worst_last:.4f}")
    print(f"arm goals seen: {sorted(arm_seen)}; robots whose arm moved: {int(arm_moved.sum())} of {n}")
    print(f"largest change in base speed in one control step: {biggest_jump:.3f} m/s")
    print(f"falls: {falls} in {robot_seconds:.0f} robot-seconds ({falls / robot_seconds * 20:.3f} per 20 s episode); time-outs: {timeouts}")
    check(("hand_off" in on) == (started > 0), "hand-offs are wrong for this task")
    if "hand_off" in on:
        check(worst_cmd < 1e-6, "a scripted robot's policy saw a command")
        check(worst_last < 1e-4, "a scripted robot's last action is not from its joints")
    check(("arm" in on) == (len(arm_seen) > 1), "arm poses are wrong for this task")
    check(("shoves" in on) == (biggest_jump > 0.15), "shoves are wrong for this task")

print("PROBLEMS:" if problems else "OK", problems if problems else "")
sys.exit(1 if problems else 0)
