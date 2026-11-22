#!/usr/bin/env python3
"""The oracle, training-simulator side (training plan, part 5.7). Must pass before any training run.

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/oracle.py [--num_envs 16]

Checks the robot Isaac Lab built against scorpion/model.json, then that it stands for 5 s on its
motors and survives a 5 cm drop, like check_model.py does in MuJoCo. Exits 1 on any problem and
prints how many things it checked.
"""
import argparse
import contextlib
import json
import math
import sys

import warp as wp

wp.config.enable_backward = False

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import resolve_task_config, setup_preset_cli  # noqa: E402

import scorbi_lab  # noqa: E402,F401
from scorbi_lab.robot import FEET, JOINTS, LEG_JOINTS, MODEL, MOTOR, STAND, STAND_HEIGHT  # noqa: E402

TASK = "Scorbi-Velocity-Flat"
parser = argparse.ArgumentParser()
parser.add_argument("--num_envs", type=int, default=1024)
parser.add_argument("--json", default=None, help="write the measurements here")
parser.add_argument("--trace", type=int, default=0, help="print robot 0 for this many control steps")
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args

problems: list[str] = []
checked = 0
out: dict = {}


def check(ok: bool, what: str) -> None:
    global checked
    checked += 1
    if not ok:
        problems.append(what)
        print("PROBLEM:", what)


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


env_cfg, _ = resolve_task_config(TASK, "")
env_cfg.scene.num_envs = args.num_envs
# A still test: no scatter at reset, everyone told to stand, no falls ending the episode.
# The reset events stay, with no scatter: they are what puts the robot in its initial state.
env_cfg.events.reset_base.params["pose_range"] = {}
env_cfg.events.reset_robot_joints.params["position_range"] = (0.0, 0.0)
TASK_STANDING = env_cfg.commands.base_velocity.rel_standing_envs
env_cfg.commands.base_velocity.rel_standing_envs = 1.0
env_cfg.terminations.base_contact = None
env_cfg.terminations.bad_orientation = None
env_cfg.observations.policy.enable_corruption = False

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    env = gym.make(TASK, cfg=env_cfg)
    cleanup.callback(env.close)
    u = env.unwrapped
    robot = u.scene["robot"]
    sensor = u.scene["contact_forces"]
    d = robot.data
    env.reset()

    # ── names ────────────────────────────────────────────────────────────
    names = list(robot.joint_names)
    bodies = list(robot.body_names)
    print("Isaac Lab joint order:", names)
    print("bodies:", bodies)
    print("contact sensor names:", list(sensor.sensor_names))
    out["joint_names"] = names
    out["body_names"] = bodies
    check(sorted(names) == sorted(JOINTS), f"joints differ: {sorted(set(names) ^ set(JOINTS))}")
    for f in FEET:
        check(f in bodies, f"foot body {f} missing")
        check(any(f in s for s in sensor.sensor_names), f"foot {f} has no contact sensor")
    check(any("base" in s for s in sensor.sensor_names), "base has no contact sensor")
    action_term = u.action_manager.get_term("joint_pos")
    action_joints = [names[i] for i in action_term._joint_ids] if hasattr(action_term, "_joint_ids") else None
    print("action joints:", action_joints)
    out["action_joints"] = action_joints
    check(action_joints == LEG_JOINTS, f"action joints are not the 12 leg joints in model order: {action_joints}")

    # ── numbers against model.json, joint by joint, by name ──────────────
    mass = d.body_mass.torch[0].sum().item()
    out["mass_kg"] = mass
    print(f"mass {mass * 1000:.1f} g (model.json {MODEL['mass'] * 1000:.1f} g)")
    check(close(mass, MODEL["mass"], 0.001), f"mass {mass * 1000:.1f} g")
    limits = d.joint_pos_limits.torch[0]
    per_joint = {
        "stiffness": (d.joint_stiffness.torch[0], MOTOR["kp"], 1e-4),
        "damping": (d.joint_damping.torch[0], MOTOR["kv"] + MOTOR["damping"], 1e-4),
        "armature": (d.joint_armature.torch[0], MOTOR["armature"], 1e-6),
        "friction": (d.joint_friction_coeff.torch[0], MOTOR["frictionloss"], 1e-5),
        "effort limit": (d.joint_effort_limits.torch[0], MOTOR["effort"], 1e-4),
        "velocity limit": (d.joint_vel_limits.torch[0], MOTOR["velocity"], 1e-3),
    }
    default_pos = d.default_joint_pos.torch[0]
    for j in MODEL["joints"]:
        i = names.index(j["name"])
        check(close(limits[i, 0].item(), j["lower"], 1e-4), f"{j['name']} lower limit {limits[i, 0].item():.5f} vs {j['lower']:.5f}")
        check(close(limits[i, 1].item(), j["upper"], 1e-4), f"{j['name']} upper limit {limits[i, 1].item():.5f} vs {j['upper']:.5f}")
        check(close(default_pos[i].item(), STAND[j["name"]], 1e-5), f"{j['name']} default {default_pos[i].item():.5f} vs stand {STAND[j['name']]:.5f}")
        for label, (values, want, tol) in per_joint.items():
            check(close(values[i].item(), want, tol), f"{j['name']} {label} {values[i].item():.5f} vs {want}")
    check(close(u.step_dt, 0.02, 1e-9), f"control step {u.step_dt}")
    out["control_dt"] = u.step_dt
    out["physics_dt"] = u.physics_dt

    # ── stand 5 s, then a 5 cm drop, with zero action ────────────────────
    zero = torch.zeros((u.num_envs, 12), device=u.device)
    foot_ids = [list(sensor.sensor_names).index(next(s for s in sensor.sensor_names if f in s)) for f in FEET]
    weight = MODEL["mass"] * 9.81
    for label, lift in (("stand", 0.0), ("drop from 5 cm", 0.05)):
        env.reset()
        if lift:
            pose = d.root_link_pose_w.torch.clone()
            pose[:, 2] += lift
            robot.write_root_pose_to_sim_index(root_pose=pose)
        peak = torch.zeros(u.num_envs, device=u.device)
        with torch.inference_mode():
            for step in range(250):
                env.step(zero)
                peak = torch.maximum(peak, robot.actuators.applied_effort.torch.abs().amax(dim=1))
                if args.trace and step < args.trace:
                    forces = sensor.data.net_forces_w.torch[0, :, 2]
                    touching = [n for n, f in zip(sensor.sensor_names, forces.tolist()) if abs(f) > 1e-3]
                    print(
                        f"  {label} step {step + 1}: z {d.root_link_pos_w.torch[0, 2].item() * 1000:.2f} mm,"
                        f" joint error {(d.joint_pos.torch[0] - d.default_joint_pos.torch[0]).abs().amax().item():.4f} rad,"
                        f" torque {robot.actuators.applied_effort.torch[0].abs().amax().item():.3f} N m, touching {touching}"
                    )
        height = d.root_link_pos_w.torch[:, 2] - u.scene.env_origins[:, 2]
        tilt = torch.rad2deg(torch.acos((-d.projected_gravity_b.torch[:, 2]).clamp(-1, 1)))
        feet_force = sensor.data.net_forces_w.torch[:, foot_ids, 2]
        err = (d.joint_pos.torch - d.default_joint_pos.torch).abs().amax().item()
        row = {
            "height_mm": [height.min().item() * 1000, height.max().item() * 1000],
            "tilt_deg_max": tilt.max().item(),
            "feet_force_n_mean": feet_force.mean(dim=0).tolist(),
            "feet_force_sum_over_weight": (feet_force.sum(dim=1).mean().item() / weight),
            "joint_error_rad_max": err,
            "peak_torque_share_of_limit": peak.max().item() / MOTOR["effort"],
        }
        out[label] = row
        print(label, json.dumps(row))
        check(0.06 < height.min().item() and height.max().item() < 0.08, f"{label}: base height {row['height_mm']} mm")
        check(tilt.max().item() < 2.0, f"{label}: tilt {tilt.max().item():.2f} degrees")
        check(bool((feet_force > 0.1).all()), f"{label}: a foot reports no contact force: {row['feet_force_n_mean']}")
        check(0.8 < row["feet_force_sum_over_weight"] < 1.2, f"{label}: feet carry {row['feet_force_sum_over_weight']:.2f} of the weight")
        check(math.isfinite(err) and err < 0.1, f"{label}: joints {err:.3f} rad from the stand")

    # ── the command mix, and what a motionless robot earns from it ───────
    # The robots are standing still on zero action. Give them the task's real commands and read the
    # reward they are paid for doing nothing. Robots told to stand are left out: they earn honestly.
    term = u.command_manager.get_term("base_velocity")
    c = term.cfg
    c.rel_standing_envs = TASK_STANDING
    everyone = torch.arange(u.num_envs, device=u.device)
    full = sum(u.reward_manager.get_term_cfg(n).weight for n in u.reward_manager.active_terms if u.reward_manager.get_term_cfg(n).weight > 0)
    paid, commands, standing = [], [], []
    with torch.inference_mode():
        for _ in range(8):
            term._resample_command(everyone)
            total = torch.zeros(u.num_envs, device=u.device)
            for step in range(6):
                env.step(zero)
                if step >= 2:
                    total += u.reward_manager._step_reward.sum(dim=1)
            paid.append(total / 4 / full)
            commands.append(term.vel_command_b.clone())
            standing.append(term.is_standing_env.clone())
    paid, commands, standing = torch.cat(paid), torch.cat(commands), torch.cat(standing)
    speed, turn = torch.linalg.norm(commands[:, :2], dim=1), commands[:, 2].abs()
    spin = ~standing & (speed == 0)
    drive = ~standing & ~spin
    moving = ~standing
    r = c.ranges
    mix = {
        "commands_sampled": int(commands.shape[0]),
        "standing_share": standing.float().mean().item(),
        "spin_share_of_moving": (spin.sum() / moving.sum()).item(),
        "straight_share_of_drive": ((turn == 0) & drive).sum().item() / drive.sum().item(),
        "slowest_drive_m_s": speed[drive].min().item(),
        "slowest_spin_rad_s": turn[spin].min().item(),
        "motionless_share_of_income": {
            "moving": paid[moving].mean().item(),
            "drive": paid[drive].mean().item(),
            "spin": paid[spin].mean().item(),
            "told_to_stand": paid[standing].mean().item(),
        },
    }
    out["command_mix"] = mix
    print("command mix", json.dumps(mix))
    check(bool((commands[standing] == 0).all()), "a robot told to stand has a command")
    check(close(mix["standing_share"], TASK_STANDING, 0.03), f"standing share {mix['standing_share']:.3f} vs {TASK_STANDING}")
    check(close(mix["spin_share_of_moving"], c.rel_spin_envs, 0.03), f"spin share {mix['spin_share_of_moving']:.3f} vs {c.rel_spin_envs}")
    check(mix["slowest_drive_m_s"] >= c.min_speed - 1e-5, f"a driving robot is told to walk at {mix['slowest_drive_m_s']:.4f} m/s")
    check(mix["slowest_spin_rad_s"] >= c.min_turn - 1e-5, f"a spinning robot is told to turn at {mix['slowest_spin_rad_s']:.4f} rad/s")
    check(not bool(((turn > 0) & (turn < c.min_turn - 1e-5)).any()), "a turn rate between zero and the floor was commanded")
    check(bool((commands[:, 0] >= r.lin_vel_x[0] - 1e-5).all() and (commands[:, 0] <= r.lin_vel_x[1] + 1e-5).all()), "forward command outside its range")
    check(bool((commands[:, 1] >= r.lin_vel_y[0] - 1e-5).all() and (commands[:, 1] <= r.lin_vel_y[1] + 1e-5).all()), "sideways command outside its range")
    check(bool((commands[:, 2] >= r.ang_vel_z[0] - 1e-5).all() and (commands[:, 2] <= r.ang_vel_z[1] + 1e-5).all()), "turn command outside its range")
    check(mix["motionless_share_of_income"]["told_to_stand"] > 0.95, f"standing when told to earns only {mix['motionless_share_of_income']['told_to_stand']:.2f}")
    check(mix["motionless_share_of_income"]["moving"] < 0.30, f"a motionless robot earns {mix['motionless_share_of_income']['moving']:.1%} of a walking robot's income (limit 30%)")

out["checked"] = checked
out["problems"] = problems
if args.json:
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1)
print(f"\n{checked} checks, {len(problems)} problems")
if problems:
    print("PROBLEMS:", *problems, sep="\n  ")
    sys.exit(1)
print("ok")
