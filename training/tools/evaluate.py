#!/usr/bin/env python3
"""The per-command evaluation, which is also the footage (training plan, part 6; Account 1 strategy, part 8).

    cd /workspace/isaaclab && uv run python /workspace/Scorbi/training/tools/evaluate.py \
        --run logs/rsl_rl/scorbi_flat/<run> [--iterations all|last|0,5,20] [--seeds 32] [--detail_at first,last]
        [--noise_std 1.0] [--do_nothing] [--cells stand,forward_top --seeds 100 --batch swarm]

One launch rolls every listed checkpoint out on 13 fixed commands, with the same seeds every time,
for 20 s, with no exploration noise unless --noise_std is given. An episode does not stop at a
fall: the fall is timed and labelled, and the robot is recorded for the whole 20 s, so the footage
shows what happens after it. Numbers such as speed, reward and torque count only up to the fall.

Written to <run>/scorbi/eval/<iteration>[_<batch>]/:

  poses.npz      50 Hz, one row per control step and robot: base position (x and y from the
                 robot's start, z above the floor), base orientation, the 15 joint angles in the
                 model's order, and which feet touch the floor. This is all a renderer needs.
  episodes.json  one entry per episode: cell, seed, command, pass or fail, the fall and its time,
                 the fail label, the funny score, speed achieved on each axis, parked share, tilt,
                 total reward and each reward term, torque with the motor mark, any shove; then
                 the picked moments, the per-command summary and the gait read from the contacts.
  detail.npz     full detail at 100 Hz for the picked moments, at the checkpoints in --detail_at:
                 joint angles, speeds and torques, actions, the command, foot forces and positions,
                 body position, orientation and velocity, every reward term, and any shove.
                 Any other episode can be recorded again in full from its checkpoint and seed.

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
from scorbi_lab import ladder  # noqa: E402
from scorbi_lab.robot import FEET, JOINTS, LEG_JOINTS, MODEL, MOTOR  # noqa: E402

SECONDS = 20.0
SHOVE_AT = 5.0
SHOVE_SPEED = 0.10  # m/s added to the base, sideways to a seeded direction
RATED_TORQUE = 0.36  # N m: the motor's everyday rating, 3.7 kg cm
STAND_HEIGHT = 0.0717  # m: the base above the floor when standing in this simulator (research 0001)
BODY_LENGTH = 0.30  # m, as Account 1's tests count it
FALL_TILT = math.radians(60.0)
DETAIL_HZ = 100
# The ball of skill 5 (THE SHOVE): a real simulated ball. It waits on the floor to one seeded side of the robot and is
# thrown at the body three times, each time from wherever it came to rest, so a recording has no cut and no jump.
BALL_HITS_AT = (5.0, 10.0, 15.0)  # s
BALL_FROM = 0.8  # m from the robot when the episode starts
BALL_AIM = 0.07  # m above the floor: the middle of the body
BALL_DRAG = 0.95  # between throws the ball's speed is multiplied by this every control step, so it stays in the shot
BALL_COLOUR = (1.0, 0.45, 0.40)  # coral

# name, (forward m/s, sideways m/s, turn rad/s), shoved, the Account 1 skill it feeds
CELLS = [
    ("stand", (0.0, 0.0, 0.0), False, "1 STAND"),
    ("forward_slow", (0.06, 0.0, 0.0), False, "2 FIRST STEPS"),
    ("forward_top", (0.12, 0.0, 0.0), False, "2 FIRST STEPS"),
    ("backward", (-0.10, 0.0, 0.0), False, "6 MOONWALK"),
    ("sideways_left", (0.0, 0.08, 0.0), False, "7 CRAB WALK"),
    ("sideways_right", (0.0, -0.08, 0.0), False, "7 CRAB WALK"),
    ("turn_left", (0.0, 0.0, 1.0), False, "4 SPIN"),
    ("turn_right", (0.0, 0.0, -1.0), False, "4 SPIN"),
    ("curve_left", (0.08, 0.0, 0.5), False, "16 FOLLOW ME"),
    ("curve_right", (0.08, 0.0, -0.5), False, "16 FOLLOW ME"),
    ("diagonal", (0.07, 0.05, 0.0), False, "Skill Wall"),
    ("forward_shoved", (0.08, 0.0, 0.0), True, "5 THE SHOVE"),
    ("stand_shoved", (0.0, 0.0, 0.0), True, "5 THE SHOVE"),
]
ALIVE_LABELS = ("turtle", "faceplant", "worm", "timber")

parser = argparse.ArgumentParser()
parser.add_argument("--run", required=True, help="the run's folder under logs/rsl_rl/scorbi_flat/")
parser.add_argument("--iterations", default="all", help="all, last, or a list such as 0,5,20")
parser.add_argument("--seeds", type=int, default=32, help="seeds per cell: 0 to seeds-1")
parser.add_argument("--cells", default=None, help="a list of cells; default all 13")
parser.add_argument("--noise_std", type=float, default=0.0, help="exploration noise on the actions; 0 = none")
parser.add_argument("--do_nothing", action="store_true", help="the control arm: zero actions instead of the policy")
parser.add_argument("--batch", default=None, help="folder suffix; default from the options")
parser.add_argument("--shove_speeds", default=None, help="a shove ladder, such as 0.2,0.3,0.5 (m/s): only the two shoved commands, once per speed; batch 'extra'")
parser.add_argument("--ball_speeds", default=None, help="skill 5 with a real ball, such as 3,5,7 (m/s): the two shoved commands, three hits each from seeded sides; batch 'ball'")
parser.add_argument("--ball_mass", type=float, default=0.2, help="kg")
parser.add_argument("--ball_radius", type=float, default=0.035, help="m")
parser.add_argument("--detail_at", default="first,last", help="iterations recorded in full detail: a list, first, last, all or none")
parser.add_argument("--detail_seeds", type=int, default=4, help="clean seeds per cell kept in full detail at the first and last checkpoint; half as many at the others")
parser.add_argument("--skip_done", action="store_true", help="skip checkpoints that already have episodes.json")
add_launcher_args(parser)
parser.set_defaults(device=None, visualizer=["newton_gl"])
args, hydra_args = setup_preset_cli(parser, sys.argv[1:])
sys.argv = [sys.argv[0]] + hydra_args

run = os.path.abspath(args.run)
manifest = json.load(open(os.path.join(run, "scorbi", "manifest.json")))
TASK = manifest.get("task") or "Scorbi-Velocity-Flat"
saved = [c["iteration"] for c in json.load(open(os.path.join(run, "scorbi", "checkpoints.json")))]


def listed(text: str) -> list[int]:
    if text == "none":
        return []
    if text == "all":
        return list(saved)
    return sorted({saved[0] if p == "first" else saved[-1] if p == "last" else int(p) for p in text.split(",")} & set(saved))  # unsaved iterations are dropped


iterations = [0] if args.do_nothing else listed(args.iterations)
detail_at = set(listed(args.detail_at)) & set(iterations)
batch = args.batch or ("do_nothing" if args.do_nothing else "noise" if args.noise_std else "extra" if args.shove_speeds else "ball" if args.ball_speeds else "")
# name, command, shove speed in m/s (0 = none), skill
cells = [(name, cmd, SHOVE_SPEED if shoved else 0.0, skill) for name, cmd, shoved, skill in CELLS if args.cells is None or name in args.cells.split(",")]
if args.shove_speeds:  # the same two shoved commands at harder shoves: forward_shoved_30 is 0.30 m/s
    cells = [(f"{name}_{round(float(v) * 100):02d}", cmd, float(v), skill) for v in args.shove_speeds.split(",") for name, cmd, shoved, skill in CELLS if shoved]
BALL = bool(args.ball_speeds)
if BALL:  # stand_ball_500 is the stand command hit by the ball at 5.00 m/s; the third field is then the ball's speed
    cells = [(f"{name.replace('_shoved', '_ball')}_{round(float(v) * 100):03d}", cmd, float(v), skill) for v in args.ball_speeds.split(",") for name, cmd, shoved, skill in CELLS if shoved]
N = len(cells) * args.seeds
STEPS = int(round(SECONDS / 0.02))
ROWS = 2 * STEPS + 1

env_cfg, agent_cfg = resolve_task_config(TASK, "rsl_rl_cfg_entry_point")
env_cfg.scene.num_envs = N
env_cfg.seed = 0
env_cfg.observations.policy.enable_corruption = False
env_cfg.events.reset_base.params["pose_range"] = {}
env_cfg.events.reset_robot_joints.params["position_range"] = (0.0, 0.0)
for name, event in list(vars(env_cfg.events).items()):  # no random shoves and no randomised robot: the nominal one
    if getattr(event, "mode", None) in ("interval", "startup"):
        setattr(env_cfg.events, name, None)
action_cfg = env_cfg.actions.joint_pos  # and nothing between the policy and the servos: no arm moves, hand-offs, delay or zero offset
if hasattr(action_cfg, "handoff_every_s"):
    action_cfg.arm_poses, action_cfg.handoff_every_s, action_cfg.delay_steps, action_cfg.zero_offset = None, 0.0, 0, 0.0
env_cfg.commands.base_velocity.resampling_time_range = (1.0e6, 1.0e6)
env_cfg.commands.base_velocity.rel_standing_envs = 0.0
# A fall does not end the episode here. It is timed with the task's own rule instead (below).
env_cfg.terminations.base_contact = None
env_cfg.terminations.bad_orientation = None
if hasattr(env_cfg.terminations, "blow_up"):
    env_cfg.terminations.blow_up = None  # watched for below instead
env_cfg.episode_length_s = 1000.0
if BALL:
    import isaaclab.sim as sim_utils
    from isaaclab.assets import RigidObjectCfg

    env_cfg.scene.ball = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Ball",
        spawn=sim_utils.SphereCfg(
            radius=args.ball_radius,
            rigid_props=sim_utils.UsdPhysicsRigidBodyCfg(),
            mass_props=sim_utils.MassCfg(mass=args.ball_mass),
            collision_props=sim_utils.UsdPhysicsCollisionCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=BALL_COLOUR),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(-BALL_FROM, 0.0, args.ball_radius)),  # moved to its seeded side at the start
    )

with launch_simulation(env_cfg, args), contextlib.ExitStack() as cleanup:
    import gymnasium as gym
    from isaaclab_rl.entrypoints.backends.train_rsl_rl import check_rsl_rl_version, create_rsl_rl_runner, handle_deprecated_rsl_rl_cfg

    env = gym.make(TASK, cfg=env_cfg)
    cleanup.callback(env.close)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    u = env.unwrapped
    device = u.device
    robot = u.scene["robot"]
    sensor = u.scene["contact_forces"]
    d = robot.data
    names = list(robot.joint_names)
    order = [names.index(j) for j in JOINTS]
    leg_cols = [names.index(j) for j in LEG_JOINTS]
    legs_of = [[names.index(j) for j in LEG_JOINTS if j.startswith(p)] for p in ("fl", "fr", "rl", "rr")]
    sensor_names = list(sensor.sensor_names)
    foot_sensor = [sensor_names.index(next(s for s in sensor_names if f in s)) for f in FEET]
    base_sensor = sensor_names.index(next(s for s in sensor_names if s.split("/")[-1] == "base"))
    bodies = list(robot.body_names)
    foot_body = [bodies.index(f) for f in FEET]
    term = u.command_manager.get_term("base_velocity")
    reward_names = list(u.reward_manager.active_terms)
    R = len(reward_names)

    runner = None
    if not args.do_nothing:
        # the same config clean-up the training entry point does before it builds the runner
        agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, check_rsl_rl_version())
        runner = create_rsl_rl_runner(env, agent_cfg)

    # ── the same start for the same seed ─────────────────────────────────
    cell_of = np.repeat(np.arange(len(cells)), args.seeds)
    seed_of = np.tile(np.arange(args.seeds), len(cells))
    scatter = np.stack([np.random.default_rng(1000 + s).uniform(-0.05, 0.05, len(JOINTS)) for s in seed_of])
    shove_angle = np.array([np.random.default_rng(2000 + s).uniform(0, 2 * math.pi) for s in seed_of])
    ball_angle = shove_angle  # the side the ball waits on: the direction the shove comes from
    ball = u.scene["ball"] if BALL else None
    cmd_np = np.array([cells[c][1] for c in cell_of], dtype=np.float32)
    commands = torch.tensor(cmd_np, device=device)
    shove_speed = np.array([cells[c][2] for c in cell_of], dtype=np.float32)
    shoved = torch.tensor((shove_speed > 0) & (not BALL), device=device)
    moving_axis = commands.abs() > 1e-6
    planar = commands[:, :2] / commands[:, :2].norm(dim=1, keepdim=True).clamp(min=1e-9)
    kick = torch.tensor(np.stack([np.cos(shove_angle), np.sin(shove_angle)], 1) * shove_speed[:, None], dtype=torch.float32, device=device)
    origin = u.scene.env_origins.clone()  # each robot's own patch of floor: z is then height above the floor
    limits = d.soft_joint_pos_limits.torch
    identity = d.default_root_pose.torch[0, 3:7].tolist()
    quat_order = "xyzw" if abs(identity[3]) > 0.5 else "wxyz"

    # ── full detail: one row per 0.01 s ──────────────────────────────────
    columns, width = {}, 0
    for key, n in (("root_pos", 3), ("root_quat", 4), ("lin_vel_body", 3), ("ang_vel_body", 3), ("joint_pos", 15), ("joint_vel", 15),
                   ("joint_torque", 15), ("action", 12), ("command", 3), ("foot_force", 12), ("foot_pos", 12), ("base_force", 3),
                   ("reward_terms", R), ("shove", 2)) + ((("ball_pos", 3),) if BALL else ()):
        columns[key] = [width, width + n]
        width += n
    detail_buf = torch.zeros(ROWS, N, width, device=device) if detail_at else None
    col = lambda k: slice(*columns[k])  # noqa: E731
    hook = {"on": False, "k": 0, "t": 0, "action": None}
    half = u.cfg.decimation // 2

    def write_detail(row: int) -> None:
        b = detail_buf[row]
        b[:, col("root_pos")] = d.root_link_pos_w.torch - origin
        b[:, col("root_quat")] = d.root_link_quat_w.torch
        b[:, col("lin_vel_body")] = d.root_link_lin_vel_b.torch
        b[:, col("ang_vel_body")] = d.root_link_ang_vel_b.torch
        b[:, col("joint_pos")] = d.joint_pos.torch[:, order]
        b[:, col("joint_vel")] = d.joint_vel.torch[:, order]
        b[:, col("joint_torque")] = robot.actuators.applied_effort.torch[:, order]
        if hook["action"] is not None:
            b[:, col("action")] = hook["action"]
        b[:, col("command")] = commands
        forces = sensor.data.net_forces_w.torch
        b[:, col("foot_force")] = forces[:, foot_sensor].reshape(N, 12)
        b[:, col("foot_pos")] = (d.body_link_pos_w.torch[:, foot_body] - origin[:, None]).reshape(N, 12)
        b[:, col("base_force")] = forces[:, base_sensor]
        if BALL:
            b[:, col("ball_pos")] = ball.data.root_link_pos_w.torch - origin

    scene_update = u.scene.update

    def update(dt):
        scene_update(dt)
        if hook["on"]:
            hook["k"] += 1
            if hook["k"] % half == 0:
                write_detail(2 * (hook["t"] - 1) + hook["k"] // half)

    u.scene.update = update
    physics = u.sim.physics_manager
    folded = bool(u._physics_handles_decimation)  # the backend runs the 4 physics steps of a control step in one call

    def set_detail(on: bool) -> None:
        """For full detail the 4 physics steps are run one by one, so the state in between can be read."""
        if folded:
            physics.set_decimation(1 if on else u.cfg.decimation)
            u._physics_handles_decimation = not on
        hook["on"] = on

    def rollout(iteration: int, detail: bool) -> dict:
        policy = None
        checkpoint = None
        if runner is not None:
            checkpoint = os.path.join(run, "scorbi", f"ckpt_{iteration}.pt")
            runner.load(checkpoint)
            policy = runner.get_inference_policy(device=device)
        set_detail(False)
        env.reset()
        start = d.default_joint_pos.torch.clone()
        start[:, order] += torch.tensor(scatter, dtype=torch.float32, device=device)
        start = start.clamp(limits[..., 0], limits[..., 1])
        robot.write_joint_position_to_sim_index(position=start)
        robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(start))
        term.vel_command_b[:] = commands
        term.is_standing_env[:] = False
        obs = env.get_observations()
        set_detail(detail)

        z = lambda *shape, **kw: torch.zeros(*shape, device=device, **kw)  # noqa: E731
        root_pos, root_quat, joint_pos = z(STEPS + 1, N, 3), z(STEPS + 1, N, 4), z(STEPS + 1, N, len(JOINTS))
        contact = z(STEPS + 1, N, 4, dtype=torch.bool)
        ball_pos = z(STEPS + 1, N, 3) if BALL else None
        hit_steps = [int(round(at / 0.02)) + 1 for at in BALL_HITS_AT] if BALL else []
        hit_before, hit_change, hit_side, hit_until = z(len(BALL_HITS_AT), N, 2), z(len(BALL_HITS_AT), N), z(len(BALL_HITS_AT), N, 2), z(N)
        if BALL:
            pose = ball.data.default_root_pose.torch.clone()
            side = torch.tensor(np.stack([np.cos(ball_angle), np.sin(ball_angle)], 1), dtype=torch.float32, device=device)
            pose[:, :2] = d.root_link_pos_w.torch[:, :2] - side * BALL_FROM
            pose[:, 2] = origin[:, 2] + args.ball_radius
            ball.write_root_pose_to_sim_index(root_pose=pose)
            ball.write_root_velocity_to_sim_index(root_velocity=z(N, 6))

        def snapshot(t: int) -> None:
            root_pos[t] = d.root_link_pos_w.torch - origin
            root_quat[t] = d.root_link_quat_w.torch
            joint_pos[t] = d.joint_pos.torch[:, order]
            contact[t] = sensor.data.net_forces_w.torch[:, foot_sensor].norm(dim=-1) > 0.3
            if BALL:
                ball_pos[t] = ball.data.root_link_pos_w.torch - origin

        alive = torch.ones(N, dtype=torch.bool, device=device)
        s = {k: z(N) for k in ("fell_step", "fall_tilt", "fall_height", "fall_gx", "limit_legs", "over15", "over15_at_fall", "measured", "parked",
                               "tilt_alive", "tilt_settled", "tilt_all", "height_min", "height_max", "height_sum", "vz_max", "spin_steps", "w_peak", "v_peak",
                               "spin_left", "spin_right", "glitch_step", "turtle_steps", "post_touch", "post_progress", "flips", "joint_speed", "reward", "steps", "yaw_6s", "yaw_all")}
        s["height_min"] += 10.0
        fall_cause = z(N, dtype=torch.long)
        vel_sum, reward_terms = z(N, 3), z(N, R)
        measured_terms: dict[str, torch.Tensor] = {}
        torque_peak, torque_sum, at_limit = z(N, len(JOINTS)), z(N, len(JOINTS)), z(N, len(JOINTS))
        noise = torch.Generator(device=device).manual_seed(iteration * 7919 + 1)
        previous = z(N, 12)
        pushes: dict[int, list[dict]] = {}
        began = time.time()

        snapshot(0)
        if detail:
            detail_buf.zero_()
            hook["action"] = None
            write_detail(0)
        with torch.inference_mode():
            for t in range(1, STEPS + 1):
                actions = z(N, 12) if policy is None else policy(obs)
                if args.noise_std:
                    actions = actions + args.noise_std * torch.randn(actions.shape, generator=noise, device=device)
                if t == int(round(SHOVE_AT / 0.02)) + 1:
                    vel = d.root_com_vel_w.torch.clone()
                    vel[:, :2] += kick * shoved[:, None]
                    robot.write_root_velocity_to_sim_index(root_velocity=vel)
                    if detail:
                        detail_buf[2 * (t - 1), :, col("shove")] = kick * shoved[:, None]
                    for i in torch.nonzero(shoved).flatten().tolist():
                        pushes[i] = [{"at_seconds": SHOVE_AT, "speed_change_m_s": float(shove_speed[i]), "direction": [float(np.cos(shove_angle[i])), float(np.sin(shove_angle[i])), 0.0],
                                     "impulse_newton_seconds": float(shove_speed[i]) * MODEL["mass"], "how": "a step change in the base's speed, in the world frame; no ball is simulated"}]
                if t in hit_steps:
                    # throw the ball from where it lies at where the body will be, on an arc that reaches the middle of the body
                    k = hit_steps.index(t)
                    speed = torch.tensor(shove_speed, device=device)
                    here = ball.data.root_link_pos_w.torch.clone()
                    body_vel = d.root_com_vel_w.torch[:, :2]
                    flight = (d.root_link_pos_w.torch[:, :2] - here[:, :2]).norm(dim=1) / speed
                    to = d.root_link_pos_w.torch[:, :2] + body_vel * flight[:, None] - here[:, :2]
                    side = to / to.norm(dim=1, keepdim=True).clamp(min=1e-6)
                    flight = to.norm(dim=1) / speed
                    velocity = z(N, 6)
                    velocity[:, :2] = side * speed[:, None]
                    velocity[:, 2] = (origin[:, 2] + BALL_AIM - here[:, 2]) / flight.clamp(min=1e-3) + 9.81 * flight / 2
                    ball.write_root_velocity_to_sim_index(root_velocity=velocity)
                    hit_before[k], hit_side[k] = body_vel, side
                    hit_until = t + (flight / 0.02).ceil() + 20  # the flight and 0.4 s after it are left to the physics
                elif BALL:
                    slow = ball.data.root_com_vel_w.torch.clone()
                    slow[t > hit_until] *= BALL_DRAG
                    ball.write_root_velocity_to_sim_index(root_velocity=slow)
                for k, at in enumerate(hit_steps):  # how much the hit changed the body's speed: the largest change in the 0.3 s after
                    if at <= t <= at + 30:
                        hit_change[k] = torch.maximum(hit_change[k], torch.nan_to_num(d.root_com_vel_w.torch[:, :2] - hit_before[k]).norm(dim=1))
                hook["t"], hook["k"], hook["action"] = t, 0, actions
                obs, rew, _, _ = env.step(actions)
                term.vel_command_b[:] = commands
                if detail:
                    detail_buf[2 * t - 1 : 2 * t + 1, :, col("reward_terms")] = u.reward_manager._step_reward
                snapshot(t)

                clean = lambda x: torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)  # noqa: E731
                # a robot the simulator lost: a state that is not a number, or a body a metre in the air
                lost = ~(torch.isfinite(root_pos[t]).all(dim=1) & torch.isfinite(joint_pos[t]).all(dim=1) & (root_pos[t, :, 2] < 1.0)) | (s["glitch_step"] > 0)
                s["glitch_step"] = torch.where(lost & (s["glitch_step"] == 0), torch.full_like(s["glitch_step"], float(t)), s["glitch_step"])
                rew = clean(rew)
                g = clean(d.projected_gravity_b.torch)
                tilt = torch.acos((-g[:, 2]).clamp(-1, 1))
                height = clean(root_pos[t, :, 2])
                v = clean(torch.cat([d.root_link_lin_vel_b.torch[:, :2], d.root_link_ang_vel_b.torch[:, 2:3]], 1))
                touching = clean(sensor.data.net_forces_w_history.torch[:, :, base_sensor]).norm(dim=-1).amax(dim=1) > 0.5
                if BALL:  # the ball pressing on the body is not the floor: while it is within reach, only a body down at belly height counts
                    ball_near = (ball_pos[t] - root_pos[t]).norm(dim=1) < 0.25
                    touching = touching & (~ball_near | (height < 0.035))
                # the task's own rule for a fall: the body touches the floor, or tips past 60 degrees
                fall = alive & (touching | (tilt > FALL_TILT) | lost)
                a = alive.float()
                s["reward"] += rew * a
                s["steps"] += a
                for k, value in ladder.measure(u).items():
                    measured_terms[k] = measured_terms.get(k, 0.0) + clean(value) * a
                reward_terms += clean(u.reward_manager._step_reward) * u.step_dt * a[:, None]  # weight x value x dt, as in the reward
                torque = clean(robot.actuators.applied_effort.torch[:, order]).abs()
                torque_peak = torch.maximum(torque_peak, torque * a[:, None])
                torque_sum += torque * a[:, None]
                at_limit += (torque > 0.98 * MOTOR["effort"]).float() * a[:, None]
                s["flips"] += ((actions * previous) < 0).float().mean(dim=1) * a
                s["joint_speed"] += clean(d.joint_vel.torch[:, leg_cols]).abs().mean(dim=1) * a
                previous = actions
                s["over15"] = torch.where(tilt > math.radians(15.0), s["over15"] + 1, torch.zeros_like(s["over15"]))
                # the moment of the fall
                q = clean(d.joint_pos.torch)
                near = ((q - limits[..., 0]) < 0.03) | ((limits[..., 1] - q) < 0.03)
                legs_at_limit = torch.stack([near[:, c].any(dim=1) for c in legs_of], 1).float().sum(dim=1)
                for key, value in (("fell_step", torch.full_like(tilt, float(t))), ("fall_tilt", tilt), ("fall_height", height), ("limit_legs", legs_at_limit),
                                   ("over15_at_fall", s["over15"])):
                    s[key] = torch.where(fall, value, s[key])
                fall_cause = torch.where(fall, torch.where(lost, 2, touching.long()), fall_cause)  # 0 = tipped past 60 degrees, 1 = the body touched the floor, 2 = the simulator lost it
                still = alive & ~fall
                alive = still
                fallen = ~alive
                # while upright
                s["tilt_alive"] = torch.where(still, torch.maximum(s["tilt_alive"], tilt), s["tilt_alive"])
                s["height_sum"] += height * a
                if t > 50:
                    vel_sum += v * still[:, None]
                    s["measured"] += still
                    slow = ((v * torch.sign(commands)) < 0.2 * commands.abs()) & moving_axis
                    s["parked"] += (slow.any(dim=1) & still).float()
                    s["tilt_settled"] = torch.where(still, torch.maximum(s["tilt_settled"], tilt), s["tilt_settled"])
                    s["height_min"] = torch.where(still, torch.minimum(s["height_min"], height), s["height_min"])
                # the whole 20 s, fall or not
                s["tilt_all"] = torch.maximum(s["tilt_all"], tilt)
                s["height_max"] = torch.maximum(s["height_max"], height)
                s["vz_max"] = torch.maximum(s["vz_max"], clean(d.root_com_vel_w.torch[:, 2]))
                s["spin_left"] = torch.where(v[:, 2] > 3.0, s["spin_left"] + 1, torch.zeros_like(s["spin_left"]))
                s["spin_right"] = torch.where(v[:, 2] < -3.0, s["spin_right"] + 1, torch.zeros_like(s["spin_right"]))
                s["spin_steps"] = torch.maximum(s["spin_steps"], torch.maximum(s["spin_left"], s["spin_right"]))  # the longest unbroken spin one way
                s["w_peak"] = torch.maximum(s["w_peak"], clean(d.root_link_ang_vel_b.torch).norm(dim=1))
                s["v_peak"] = torch.maximum(s["v_peak"], clean(d.root_link_lin_vel_b.torch).norm(dim=1))
                s["yaw_all"] += v[:, 2] * 0.02
                if t <= 300:
                    s["yaw_6s"] += v[:, 2] * 0.02
                # after the fall
                s["turtle_steps"] += (fallen & (tilt > math.radians(150.0))).float()
                s["post_touch"] += (fallen & touching).float()
                s["post_progress"] += (v[:, :2] * planar).sum(dim=1) * 0.02 * (fallen & touching).float()
                just = fallen & (t - s["fell_step"] <= 25)
                s["fall_gx"] = torch.where(just, torch.maximum(s["fall_gx"], g[:, 0]), s["fall_gx"])
        set_detail(False)
        wall = time.time() - began

        n = {k: v.cpu().numpy() for k, v in s.items()}
        fell = n["fell_step"] > 0
        glitch = n["glitch_step"].astype(int)
        for i in np.nonzero(glitch)[0]:  # hold the last good pose, so a renderer never meets a NaN
            for buf in (root_pos, root_quat, joint_pos):
                buf[glitch[i] :, i] = buf[glitch[i] - 1, i]
            contact[glitch[i] :, i] = False
        pos = root_pos.cpu().numpy()
        if BALL:
            change, sides = hit_change.cpu().numpy(), hit_side.cpu().numpy()
            for i in range(N):
                pushes[i] = [{"at_seconds": at, "ball_speed_m_s": float(shove_speed[i]), "ball_mass_kg": args.ball_mass, "ball_radius_m": args.ball_radius,
                              "direction": [float(sides[k, i, 0]), float(sides[k, i, 1]), 0.0],
                              "robot_speed_change_m_s": float(change[k, i]), "impulse_newton_seconds": float(change[k, i]) * MODEL["mass"],
                              "how": "a simulated ball thrown at the middle of the body from where it lay; the speed change is the largest in the 0.6 s after the throw"}
                             for k, at in enumerate(BALL_HITS_AT)]
        feet = contact.cpu().numpy()
        steps_alive = np.maximum(n["steps"], 1)
        mean_torque = (torque_sum.cpu().numpy()) / steps_alive[:, None]
        peak = torque_peak.cpu().numpy()
        limit_share = at_limit.cpu().numpy() / steps_alive[:, None]
        measured = n["measured"]
        achieved = vel_sum.cpu().numpy() / np.maximum(measured, 1)[:, None]
        parked = np.where(measured > 0, n["parked"] / np.maximum(measured, 1), 1.0)
        flip_rate = n["flips"] / steps_alive
        joint_speed = n["joint_speed"] / steps_alive
        terms = reward_terms.cpu().numpy()
        measured_np = {k: v.cpu().numpy() / steps_alive for k, v in measured_terms.items()}
        drift = np.linalg.norm(pos[-1, :, :2] - pos[0, :, :2], axis=1)
        along_10s = ((pos[500, :, :2] - pos[0, :, :2]) * planar.cpu().numpy()).sum(1)
        cause = fall_cause.cpu().numpy()

        def passes(i: int) -> bool:
            """Account 1 part 8.11, adapted to speed commands: see `tests` in the file's meta."""
            _, cmd, was_shoved, _ = cells[cell_of[i]]
            if fell[i]:
                return False
            if BALL:  # Account 1's test for skill 5: still standing 3 s after each of three hits. The last hit is 5 s before the end.
                return True
            if not any(cmd):
                upright = n["height_min"][i] >= 0.85 * STAND_HEIGHT
                return bool(upright and drift[i] < 0.30) if was_shoved else bool(upright and math.degrees(n["tilt_settled"][i]) < 15.0 and drift[i] < 0.10)
            for k, c in enumerate(cmd):
                if c and achieved[i, k] * np.sign(c) < 0.7 * abs(c):
                    return False
                if not c and abs(achieved[i, k]) > (0.3 if k == 2 else 0.04):
                    return False
            return bool(cmd[0] or cmd[1] or drift[i] < BODY_LENGTH)

        def label(i: int, success: bool) -> str | None:
            """Account 1 part 8.9, with thresholds for Scorbi's size."""
            _, cmd, _, _ = cells[cell_of[i]]
            moving = any(cmd)
            if glitch[i]:
                return "glitch"  # the simulator lost this robot; not footage
            if fell[i]:
                if n["turtle_steps"][i] >= 15:
                    return "turtle"  # on its back (past 150 degrees) for 0.3 s or more
                if moving and n["post_touch"][i] >= 100 and n["post_progress"][i] > 0.05:
                    return "worm"  # keeps going the commanded way on its belly
                if n["fall_gx"][i] > 0.5:
                    return "faceplant"  # nose down by 30 degrees or more within 0.5 s of the fall
                if n["vz_max"][i] > 0.4 or n["height_max"][i] > 1.6 * STAND_HEIGHT:
                    return "yeet"
                if n["spin_steps"][i] > 50:
                    return "beyblade"  # turning faster than 3 rad/s for over 1 s
                if n["over15_at_fall"][i] > 75:
                    return "timber"  # leaning past 15 degrees for over 1.5 s before it goes
                if cause[i] == 1 and math.degrees(n["fall_tilt"][i]) < 30.0:
                    return "splits" if n["limit_legs"][i] >= 2 else "pancake"  # sinks flat onto its belly
                return "tumble"
            if success:
                return None
            if n["spin_steps"][i] > 50:
                return "beyblade"
            main = int(np.argmax(np.abs(cmd)))
            if moving and achieved[i, main] * np.sign(cmd[main]) < -0.2 * abs(cmd[main]):
                return "moonwalk"  # goes the opposite way
            if flip_rate[i] > 0.3 and (not moving or parked[i] > 0.8):
                return "jackhammer"  # actions flip sign on over 30% of steps and it gets nowhere
            if moving and parked[i] > 0.8:
                return "statue" if joint_speed[i] < 0.3 else "treadmill"  # legs working, body going nowhere
            return "off_course" if moving else "wander"

        success = [passes(i) for i in range(N)]
        labels = [label(i, success[i]) for i in range(N)]
        failed = [i for i in range(N) if labels[i] and labels[i] != "glitch"]
        counts = {name: labels.count(name) for name in sorted({x for x in labels if x})}
        progress = np.where(fell, n["fell_step"] / STEPS, np.clip([achieved[i, int(np.argmax(np.abs(cmd_np[i])))] / (cmd_np[i, int(np.argmax(np.abs(cmd_np[i])))] or 1.0) if cmd_np[i].any() else 0.0 for i in range(N)], 0, 1))
        funny = np.zeros(N)
        for i in failed:  # Account 1 part 8.10, stage 1
            rarity = 1.0 - counts[labels[i]] / len(failed) if len(failed) > 1 else 1.0
            movement = min(1.0, max(n["w_peak"][i] / 10.0, n["v_peak"][i] / 0.6))
            so_close = max(0.0, 1.0 - abs(progress[i] - 0.875) / 0.5)
            clarity = 1.0 if fell[i] and n["fell_step"][i] > 50 else 0.3
            funny[i] = 0.25 * rarity + 0.20 * movement + 0.20 * so_close + 0.20 * clarity + 0.15 * (labels[i] in ALIVE_LABELS)

        episodes = []
        for i in range(N):
            name, cmd, _, skill = cells[cell_of[i]]
            mark = "red" if limit_share[i].max() > 0.05 else "amber" if mean_torque[i].max() > RATED_TORQUE or peak[i].max() > 0.8 * MOTOR["effort"] else "green"
            episodes.append({
                "index": i, "cell": name, "skill": skill, "seed": int(seed_of[i]),
                "command": {"forward_m_s": cmd[0], "sideways_m_s": cmd[1], "turn_rad_s": cmd[2]},
                "duration_seconds": SECONDS,
                "success": success[i],
                "fell": bool(fell[i]),
                "fell_at_seconds": float(n["fell_step"][i] * 0.02) if fell[i] else None,
                "fall_cause": ("tipped past 60 degrees", "the body touched the floor", "the simulator lost the robot")[cause[i]] if fell[i] else None,
                "simulation_glitch_at_seconds": float(glitch[i] * 0.02) if glitch[i] else None,
                "fail_label": labels[i],
                "funny_score": round(float(funny[i]), 3) if labels[i] else None,
                "time_upright_seconds": float(n["steps"][i] * 0.02),
                "achieved": {"forward_m_s": float(achieved[i, 0]), "sideways_m_s": float(achieved[i, 1]), "turn_rad_s": float(achieved[i, 2])} if measured[i] > 0 else None,
                "parked_share": float(parked[i]) if measured[i] > 0 and cmd_np[i].any() else None,
                "largest_tilt_deg": math.degrees(float(n["tilt_alive"][i])),
                "largest_tilt_whole_episode_deg": math.degrees(float(n["tilt_all"][i])),
                "lowest_height_m": float(n["height_min"][i]) if measured[i] > 0 else None,
                "mean_height_m": float(n["height_sum"][i] / steps_alive[i]),
                "highest_height_whole_episode_m": float(n["height_max"][i]),
                "along_command_10s_m": float(along_10s[i]),
                "turned_6s_rad": float(n["yaw_6s"][i]),
                "drift_m": float(drift[i]),
                "end_position_m": [float(x) for x in pos[-1, i, :2]],
                "action_flip_rate": float(flip_rate[i]),
                "reward": float(n["reward"][i]),
                "reward_terms": {k: float(terms[i, j]) for j, k in enumerate(reward_names)},
                "measured_terms": {k: float(v[i]) for k, v in measured_np.items()},
                "motor_mark": mark,
                "torque_peak_n_m": [round(float(x), 4) for x in peak[i]],
                "torque_mean_n_m": [round(float(x), 4) for x in mean_torque[i]],
                "share_of_time_at_limit_max": float(limit_share[i].max()),
                "pushes": pushes.get(i, []),
            })

        # ── the gait, read from the foot contacts of the forward cells ──────
        gait, gait_stats = None, None
        walkers = [i for i in range(N) if cells[cell_of[i]][0] in ("forward_slow", "forward_top") and not fell[i]]
        if walkers:
            c = feet[101:, walkers]  # steps, robots, feet (fl, fr, rl, rr)
            down = c.sum(axis=2)
            lifts = (c[:-1] & ~c[1:]).sum(axis=0).mean() / (c.shape[0] * 0.02)
            diagonal_air = ((~c[:, :, 0] & ~c[:, :, 3]) | (~c[:, :, 1] & ~c[:, :, 2])).mean()
            diagonal_together = ((c[:, :, 0] == c[:, :, 3]).mean() + (c[:, :, 1] == c[:, :, 2]).mean()) / 2
            gait_stats = {"from_cells": ["forward_slow", "forward_top"], "robots": len(walkers), "duty_factor": [float(x) for x in c.mean(axis=(0, 1))],
                          "feet_order": FEET, "lift_offs_per_foot_per_second": float(lifts), "share_of_time_three_or_more_feet_down": float((down >= 3).mean()),
                          "share_of_time_a_diagonal_pair_is_in_the_air": float(diagonal_air), "diagonal_feet_in_step": float(diagonal_together),
                          "mean_speed_m_s": float(np.mean([achieved[i, 0] for i in walkers]))}
            gait = "none" if lifts < 0.3 else "trot" if diagonal_air > 0.15 and diagonal_together > 0.7 else "crawl" if (down >= 3).mean() > 0.8 else "other"

        # ── the picked moments ───────────────────────────────────────────────
        moments, picked = [], {}
        per: dict[tuple, int] = {}
        for i in sorted(failed, key=lambda i: -funny[i]):
            key = (cell_of[i], labels[i])
            if per.get(key, 0) >= 2 or sum(m["kind"] == "fail" for m in moments) >= 16:
                continue
            per[key] = per.get(key, 0) + 1
            at = float(n["fell_step"][i]) * 0.02 if fell[i] else 5.0
            window = (max(0.0, at - 4.0), min(SECONDS, at + 2.0)) if fell[i] else (2.0, 8.0)
            moments.append({"kind": "fail", "episode": i, "start_seconds": window[0], "end_seconds": window[1], "event_seconds": at if fell[i] else None})
            picked[i] = window
        if failed:
            i = max(failed, key=lambda i: progress[i])
            moments.append({"kind": "almost", "episode": i, "start_seconds": 0.0, "end_seconds": SECONDS, "event_seconds": float(n["fell_step"][i] * 0.02) if fell[i] else None})
        for c in range(len(cells)):
            good = [i for i in range(N) if cell_of[i] == c and success[i]]
            if good:
                i = min(good, key=lambda i: (n["tilt_alive"][i], seed_of[i]))
                moments.append({"kind": "clean_success", "episode": i, "start_seconds": 0.0, "end_seconds": SECONDS, "event_seconds": None})
        if detail:
            keep = args.detail_seeds if iteration in (iterations[0], iterations[-1]) else max(1, args.detail_seeds // 2)
            for i in range(N):
                if seed_of[i] < keep:
                    moments.append({"kind": "lesson", "episode": i, "start_seconds": 0.0, "end_seconds": SECONDS, "event_seconds": None,
                                    "note": "untrained" if iteration == 0 else "clean take" if success[i] else "not a clean take"})
                    picked[i] = (0.0, SECONDS)
        for m in moments:
            i = m["episode"]
            m.update({"cell": cells[cell_of[i]][0], "seed": int(seed_of[i]), "fail_label": labels[i], "funny_score": episodes[i]["funny_score"], "detail_index": None})

        out = os.path.join(run, "scorbi", "eval", str(iteration) + (f"_{batch}" if batch else ""))
        os.makedirs(out, exist_ok=True)
        detail_meta = None
        if detail:
            chunks, index = [], []
            for k, (i, (a0, a1)) in enumerate(sorted(picked.items())):
                r0, r1 = int(round(a0 * DETAIL_HZ)), int(round(a1 * DETAIL_HZ))
                chunks.append(detail_buf[r0 : r1 + 1, i].cpu().numpy())
                index.append((i, r0, r1 - r0 + 1))
                for m in moments:
                    if m["episode"] == i and m["kind"] in ("fail", "lesson"):
                        m["detail_index"] = k
            starts = np.cumsum([0] + [c.shape[0] for c in chunks[:-1]]) if chunks else np.zeros(0)
            np.savez_compressed(os.path.join(out, "detail.npz"), data=np.concatenate(chunks) if chunks else np.zeros((0, width), np.float32),
                                episode=np.array([x[0] for x in index]), first_row=np.array([x[1] for x in index]), rows=np.array([x[2] for x in index]),
                                start=starts, columns=json.dumps(columns))
            detail_meta = {
                "rate_hz": DETAIL_HZ, "file": "detail.npz", "columns": columns,
                "layout": "data[start[k] : start[k] + rows[k]] is recording k of episode episode[k]; its first row is at first_row[k] / 100 seconds",
                "channels": {"root_pos": "metres; x and y from the start, z above the floor", "root_quat": quat_order, "lin_vel_body": "m/s, body frame", "ang_vel_body": "rad/s, body frame",
                             "joint_pos": "rad", "joint_vel": "rad/s", "joint_torque": "N m, Isaac Lab's applied effort", "action": "the policy's 12 outputs; leg target = standing pose + 0.25 x action",
                             "command": "forward m/s, sideways m/s (left positive), turn rad/s (left positive)", "foot_force": "N, world frame, x y z for each of " + ", ".join(FEET),
                             "foot_pos": "metres, as root_pos, x y z for each foot", "base_force": "N, contact force on the body", "reward_terms": "weight x value per second, for " + ", ".join(reward_names),
                             "shove": "m/s added to the base in x and y between this row and the next"},
                "joints": JOINTS, "action_joints": LEG_JOINTS,
            }
        np.savez_compressed(os.path.join(out, "poses.npz"), **({"ball_pos": ball_pos.cpu().numpy()} if BALL else {}), root_pos=pos, root_quat=root_quat.cpu().numpy(), joint_pos=joint_pos.cpu().numpy(),
                            foot_contact=feet, length=np.full(N, STEPS), fell_step=np.where(fell, n["fell_step"], -1).astype(np.int32))

        summary = []
        for c, (name, cmd, _, skill) in enumerate(cells):
            rows = [e for e in episodes if e["cell"] == name]
            ach = [e["achieved"] for e in rows if e["achieved"]]
            mean = lambda k: sum(a[k] for a in ach) / len(ach) if ach else None  # noqa: E731
            park = [e["parked_share"] for e in rows if e["parked_share"] is not None]
            summary.append({"cell": name, "skill": skill, "episodes": len(rows), "passed": sum(e["success"] for e in rows), "falls": sum(e["fell"] for e in rows),
                            "forward_m_s": mean("forward_m_s"), "sideways_m_s": mean("sideways_m_s"), "turn_rad_s": mean("turn_rad_s"),
                            "parked_share": sum(park) / len(park) if park else None, "largest_tilt_deg": max(e["largest_tilt_deg"] for e in rows),
                            "reward": sum(e["reward"] for e in rows) / len(rows),
                            "measured_terms": {k: sum(e["measured_terms"][k] for e in rows) / len(rows) for k in rows[0]["measured_terms"]},
                            "motor_marks": {m: sum(e["motor_mark"] == m for e in rows) for m in ("green", "amber", "red")},
                            "fail_labels": {k: sum(e["fail_label"] == k for e in rows) for k in sorted({e["fail_label"] for e in rows if e["fail_label"]})}})
        meta = {
            "task": TASK, "run": os.path.basename(run), "iteration": iteration, "batch": batch or "seeds",
            "checkpoint": os.path.basename(checkpoint) if checkpoint else None, "noise_std": args.noise_std, "seeds_per_cell": args.seeds,
            "rate_hz": 50, "steps": STEPS, "joints": JOINTS, "feet": FEET, "quat_order": quat_order,
            "channels": {"root_pos": "metres; x and y from where the robot started, z above the floor", "root_quat": quat_order, "joint_pos": "radians, in the order of `joints`",
                         "foot_contact": "true when the foot presses on the floor with more than 0.3 N, in the order of `feet`", "length": "steps recorded", "fell_step": "the step of the fall, or -1"},
            "start": "joint scatter of +-0.05 rad from rng(1000 + seed); shove direction from rng(2000 + seed)",
            "ball": {"mass_kg": args.ball_mass, "radius_m": args.ball_radius, "colour_rgb": BALL_COLOUR, "hits_at_seconds": BALL_HITS_AT, "starts_m_from_robot": BALL_FROM,
                     "sides": "it waits on the side the shove comes from (rng(2000 + seed)); each throw is from where the ball then lies, so the three sides differ",
                     "drag": f"between throws its speed is multiplied by {BALL_DRAG} every 0.02 s; a throw and the 0.4 s after it are left to the physics",
                     "pose": "ball_pos in poses.npz, as root_pos",
                     "test": "no fall: still standing 3 s after each of the three hits (Account 1 part 8.11, skill 5)",
                     "fall": "while the ball is within 0.25 m of the body, contact on the body counts as a fall only if the body is under 35 mm high"} if BALL else None,
            "starts": {str(k): {"scatter": dict(zip(JOINTS, scatter[k].tolist())), "shove_angle": float(shove_angle[k])} for k in range(args.seeds)},
            "fall": "the task's rule: the body touches the floor (over 0.5 N), or the robot tips past 60 degrees. The episode is recorded to the end; numbers count up to the fall.",
            "tests": {"stand": "no fall, body at 85% of standing height or more, tilt under 15 degrees after the first second, drift under 0.10 m",
                      "moving": "no fall; 70% or more of the commanded speed on each commanded axis; under 0.04 m/s and 0.3 rad/s on the others",
                      "turn": "as moving, and drifting under one body length (0.30 m)", "shoved": "the same without the tilt limit; stand may drift 0.30 m",
                      "note": "Account 1's tests ask for 5 body lengths in 10 s, which is 0.15 m/s; the website's top speed is 0.12 m/s. `along_command_10s_m` and `turned_6s_rad` give the numbers for those tests."},
            "motor_mark": {"limit_n_m": MOTOR["effort"], "rated_n_m": RATED_TORQUE, "red": "a joint within 2% of the limit for over 5% of the time upright", "amber": "average above rated, or peak over 80% of the limit"},
            "parked": "share of time, after the first second, moving at under 20% of a commanded speed",
            "measured_terms": "every reward-ladder term (scorbi_lab/ladder.py), unweighted, averaged over the time upright, whether or not this run was rewarded for it",
            "torque_order": JOINTS,
            "stepping": "the 4 physics steps of each control step run one by one" if detail else "as in training",
            "wall_seconds": wall, "cells": [c[0] for c in cells], "detail": detail_meta,
        }
        with open(os.path.join(out, "episodes.json"), "w") as f:
            json.dump({"meta": meta, "summary": summary, "gait": gait, "gait_stats": gait_stats, "moments": moments, "episodes": episodes}, f, separators=(",", ":"), default=lambda o: o.item())
        return {"iteration": iteration, "batch": meta["batch"], "episodes": N, "passed": sum(success), "falls": int(fell.sum()), "gait": gait,
                "fail_labels": counts, "moments": len(moments), "detail": bool(detail), "wall_seconds": round(wall, 1), "summary": summary, "out": out}

    index_path = os.path.join(run, "scorbi", "eval", f"index_{batch or 'seeds'}.jsonl")
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    for iteration in iterations:
        folder = os.path.join(run, "scorbi", "eval", str(iteration) + (f"_{batch}" if batch else ""))
        if args.skip_done and os.path.exists(os.path.join(folder, "episodes.json")):
            continue
        result = rollout(iteration, iteration in detail_at)
        with open(index_path, "a") as f:
            f.write(json.dumps({k: v for k, v in result.items() if k != "out"}) + "\n")
        print(f"\n{result['batch']} · iteration {iteration} · {N} episodes · passed {result['passed']} · falls {result['falls']} · gait {result['gait']} · "
              f"labels {result['fail_labels']} · {result['wall_seconds']} s{' · full detail' if result['detail'] else ''} · {result['out']}")
        print(f"{'cell':16} {'pass':>5} {'falls':>5} {'fwd':>7} {'side':>7} {'turn':>7} {'parked':>7} {'tilt':>6} {'reward':>7}  marks, labels")
        fmt = lambda x, w=7, p=3: f"{x:>{w}.{p}f}" if x is not None else " " * (w - 1) + "-"  # noqa: E731
        for row in result["summary"]:
            print(f"{row['cell']:16} {row['passed']:>5} {row['falls']:>5} {fmt(row['forward_m_s'])} {fmt(row['sideways_m_s'])} {fmt(row['turn_rad_s'])} {fmt(row['parked_share'], 7, 2)}"
                  f" {row['largest_tilt_deg']:>6.1f} {row['reward']:>7.2f}  {row['motor_marks']} {row['fail_labels']}", flush=True)
