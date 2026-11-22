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
parser.add_argument("--num_envs", type=int, default=16)
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
