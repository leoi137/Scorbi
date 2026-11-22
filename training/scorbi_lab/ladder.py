"""The reward ladder (training plan, part 5.4): one term added at a time, each priced at Scorbi's scale.

Every term here is also measured on every run, rewarded or not (`measure`), so runs can be compared.
The weights were priced on the tracking-only baseline, where tracking pays 1.5 a second
(research 0005): each term costs that policy 0.1 to 0.3 a second, and a clean walk almost nothing.
"""

import torch

from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass

import isaaclab_tasks.core.velocity.mdp as mdp

from .env_cfg import RewardsCfg, ScorbiFlatEnvCfg
from .robot import LEG_JOINTS

FOOT_AT_REST = 0.0125  # m: height of a foot's centre when it stands on the floor (measured)
FOOT_LIFT = 0.016  # m: how high the website's scripted gait lifts a foot
FEET = SceneEntityCfg("robot", body_names=".*_foot")
FEET_SENSOR = SceneEntityCfg("contact_forces", body_names=".*_foot")
LEGS = SceneEntityCfg("robot", joint_names=LEG_JOINTS, preserve_order=True)


def _feet_down(env, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    forces = env.scene.sensors[sensor_cfg.name].data.net_forces_w_history.torch[:, :, sensor_cfg.body_ids]
    return forces.norm(dim=-1).amax(dim=1) > 0.3


def action_rate(env) -> torch.Tensor:
    """How much the 12 actions changed since the last control step, squared and summed."""
    return torch.sum(torch.square(env.action_manager.action - env.action_manager.prev_action), dim=1)


def leg_torque(env, asset_cfg: SceneEntityCfg = LEGS) -> torch.Tensor:
    """The 12 leg motors' torques, squared and summed [N^2 m^2]."""
    asset = env.scene[asset_cfg.name]
    return torch.sum(torch.square(asset.actuators.applied_effort.torch[:, asset_cfg.joint_ids]), dim=1)


def foot_slip(env, sensor_cfg: SceneEntityCfg = FEET_SENSOR, asset_cfg: SceneEntityCfg = FEET) -> torch.Tensor:
    """Speed along the floor of every foot that is on the floor, summed [m/s]."""
    speed = env.scene[asset_cfg.name].data.body_link_lin_vel_w.torch[:, asset_cfg.body_ids, :2].norm(dim=-1)
    return torch.sum(speed * _feet_down(env, sensor_cfg), dim=1)


def foot_drag(env, asset_cfg: SceneEntityCfg = FEET, lift: float = FOOT_LIFT, speed_ref: float = 0.2) -> torch.Tensor:
    """A foot that moves along the floor without being lifted.

    For each foot: (how far it is from the full lift, as a share of the lift)^2 x (its speed along
    the floor / 0.2 m/s). A foot standing still costs nothing at any height; a foot swinging at
    0.2 m/s costs 1 on the floor and 0 at 16 mm.
    """
    data = env.scene[asset_cfg.name].data
    height = data.body_link_pos_w.torch[:, asset_cfg.body_ids, 2] - env.scene.env_origins[:, 2:3]
    short = torch.clamp((FOOT_AT_REST + lift - height) / lift, min=0.0, max=1.5)
    speed = data.body_link_lin_vel_w.torch[:, asset_cfg.body_ids, :2].norm(dim=-1)
    return torch.sum(torch.square(short) * speed / speed_ref, dim=1)


def body_bounce(env, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """The body's vertical speed squared [m^2/s^2] plus a tenth of its roll and pitch rate squared [rad^2/s^2]."""
    data = env.scene[asset_cfg.name].data
    return torch.square(data.root_lin_vel_b.torch[:, 2]) + 0.1 * torch.sum(torch.square(data.root_ang_vel_b.torch[:, :2]), dim=1)


def fidget_at_rest(env, command_name: str = "base_velocity", asset_cfg: SceneEntityCfg = LEGS) -> torch.Tensor:
    """When told to stand (the whole command is zero): how far the leg joints are from the stance, summed [rad]."""
    data = env.scene[asset_cfg.name].data
    away = torch.sum(torch.abs(data.joint_pos.torch[:, asset_cfg.joint_ids] - data.default_joint_pos.torch[:, asset_cfg.joint_ids]), dim=1)
    return away * (env.command_manager.get_command(command_name).abs().sum(dim=1) < 1e-6)


def step_time(env, command_name: str = "base_velocity", sensor_cfg: SceneEntityCfg = FEET_SENSOR, target: float = 0.2) -> torch.Tensor:
    """Paid at each touchdown for how long the foot was in the air, up to the scripted gait's 0.2 s; nothing when told to stand."""
    sensor = env.scene.sensors[sensor_cfg.name]
    landed = sensor.compute_first_contact(env.step_dt).torch[:, sensor_cfg.body_ids]
    air = sensor.data.last_air_time.torch[:, sensor_cfg.body_ids].clamp(max=target)
    moving = env.command_manager.get_command(command_name).abs().sum(dim=1) > 1e-6
    return torch.sum(air * landed, dim=1) * moving


def long_steps(env, command_name: str = "base_velocity", sensor_cfg: SceneEntityCfg = FEET_SENSOR, shortest: float = 0.1, target: float = 0.2) -> torch.Tensor:
    """Paid at each touchdown for how much longer than 0.1 s the foot was in the air, up to the scripted gait's 0.2 s.

    A swing shorter than 0.1 s costs; one of 0.2 s or more pays 0.1. Nothing when told to stand.
    Unlike `step_time`, the same time in the air pays more as few long swings than as many short ones.
    """
    sensor = env.scene.sensors[sensor_cfg.name]
    landed = sensor.compute_first_contact(env.step_dt).torch[:, sensor_cfg.body_ids]
    air = sensor.data.last_air_time.torch[:, sensor_cfg.body_ids].clamp(max=target) - shortest
    moving = env.command_manager.get_command(command_name).abs().sum(dim=1) > 1e-6
    return torch.sum(air * landed, dim=1) * moving


def paired_steps(env, command_name: str = "base_velocity", sensor_cfg: SceneEntityCfg = FEET_SENSOR, shortest: float = 0.1, target: float = 0.2) -> torch.Tensor:
    """`long_steps`, paid only when the foot stood on the floor at least as long as it then swung.

    `long_steps` alone was won by hopping: 0.2 s in the air and 0.06 s on the floor (research 0009).
    A swing that follows a shorter stance pays nothing here, so the longest-paying gait is the scripted
    one: 0.2 s down, 0.2 s up.
    """
    sensor = env.scene.sensors[sensor_cfg.name]
    landed = sensor.compute_first_contact(env.step_dt).torch[:, sensor_cfg.body_ids]
    air = sensor.data.last_air_time.torch[:, sensor_cfg.body_ids]
    stood = sensor.data.last_contact_time.torch[:, sensor_cfg.body_ids] >= air.clamp(max=target)
    moving = env.command_manager.get_command(command_name).abs().sum(dim=1) > 1e-6
    return torch.sum((air.clamp(max=target) - shortest) * landed * stood, dim=1) * moving


# name, function, weight. The order is the ladder's.
LADDER = [
    ("action_rate", action_rate, -0.05),
    ("leg_torque", leg_torque, -0.05),
    ("foot_slip", foot_slip, -1.0),
    ("foot_drag", foot_drag, -0.3),
    ("body_bounce", body_bounce, -2.0),
    ("fidget_at_rest", fidget_at_rest, -0.2),
]
# Not on the plan's ladder; measured on every run. long_steps is the probe for steps that stay too quick (research 0007).
# The reward manager multiplies by the 0.02 s step, so 25 pays 0.5 for each second a swing lasts beyond 0.1 s:
# 0.4 a second for the scripted gait (two 0.2 s swings a second per foot), nothing for the 0.1 s patter.
# paired_steps at 15 pays 0.3 a second for the scripted gait (each foot 0.2 s down, 0.2 s up).
EXTRA = [("step_time", step_time, 2.0), ("long_steps", long_steps, 25.0), ("paired_steps", paired_steps, 15.0)]

_resolved: set[int] = set()


def measure(env) -> dict[str, torch.Tensor]:
    """Every ladder term's raw value for every robot at this control step, rewarded or not."""
    if id(env) not in _resolved:
        for cfg in (FEET, FEET_SENSOR, LEGS):
            cfg.resolve(env.scene)
        _resolved.add(id(env))
    return {name: func(env) for name, func, _ in LADDER + EXTRA}


@configclass
class Ladder1RewardsCfg(RewardsCfg):
    action_rate = RewTerm(func=action_rate, weight=LADDER[0][2])
    # From the first penalty on, a fall has a price (plan 5.4): without it, ending the episode stops
    # the penalties and can become the best move. The reward manager multiplies by the 0.02 s step, so
    # -400 is 8 off per fall: more than the few seconds of penalties a fall could save.
    fell = RewTerm(func=mdp.is_terminated, weight=-400.0)


@configclass
class Ladder2RewardsCfg(Ladder1RewardsCfg):
    leg_torque = RewTerm(func=leg_torque, weight=LADDER[1][2], params={"asset_cfg": SceneEntityCfg("robot", joint_names=LEG_JOINTS, preserve_order=True)})


@configclass
class Ladder3RewardsCfg(Ladder2RewardsCfg):
    foot_slip = RewTerm(
        func=foot_slip, weight=LADDER[2][2],
        params={"sensor_cfg": SceneEntityCfg("contact_forces", body_names=".*_foot"), "asset_cfg": SceneEntityCfg("robot", body_names=".*_foot")},
    )


@configclass
class Ladder4RewardsCfg(Ladder3RewardsCfg):
    foot_drag = RewTerm(func=foot_drag, weight=LADDER[3][2], params={"asset_cfg": SceneEntityCfg("robot", body_names=".*_foot")})


@configclass
class Ladder5RewardsCfg(Ladder4RewardsCfg):
    body_bounce = RewTerm(func=body_bounce, weight=LADDER[4][2])


@configclass
class Ladder6RewardsCfg(Ladder5RewardsCfg):
    fidget_at_rest = RewTerm(func=fidget_at_rest, weight=LADDER[5][2], params={"asset_cfg": SceneEntityCfg("robot", joint_names=LEG_JOINTS, preserve_order=True)})


@configclass
class Ladder1StepsRewardsCfg(Ladder1RewardsCfg):
    """Rung 1 plus the long-steps term: a probe aimed at the quick patter rungs 1 and 2 still walk with."""

    long_steps = RewTerm(func=long_steps, weight=EXTRA[1][2], params={"sensor_cfg": SceneEntityCfg("contact_forces", body_names=".*_foot")})


# Rung 3 (foot_slip) made the walk worse (research 0008), so rungs 4 to 6 are also tried one at a time on rung 2.
@configclass
class Ladder2DragRewardsCfg(Ladder2RewardsCfg):
    foot_drag = RewTerm(func=foot_drag, weight=LADDER[3][2], params={"asset_cfg": SceneEntityCfg("robot", body_names=".*_foot")})


@configclass
class Ladder2BounceRewardsCfg(Ladder2RewardsCfg):
    body_bounce = RewTerm(func=body_bounce, weight=LADDER[4][2])


@configclass
class Ladder2FidgetRewardsCfg(Ladder2RewardsCfg):
    fidget_at_rest = RewTerm(func=fidget_at_rest, weight=LADDER[5][2], params={"asset_cfg": SceneEntityCfg("robot", joint_names=LEG_JOINTS, preserve_order=True)})


@configclass
class Ladder2PairedRewardsCfg(Ladder2RewardsCfg):
    paired_steps = RewTerm(func=paired_steps, weight=EXTRA[2][2], params={"sensor_cfg": SceneEntityCfg("contact_forces", body_names=".*_foot")})


@configclass
class Ladder1EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder1RewardsCfg = Ladder1RewardsCfg()


@configclass
class Ladder2EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder2RewardsCfg = Ladder2RewardsCfg()


@configclass
class Ladder3EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder3RewardsCfg = Ladder3RewardsCfg()


@configclass
class Ladder4EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder4RewardsCfg = Ladder4RewardsCfg()


@configclass
class Ladder5EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder5RewardsCfg = Ladder5RewardsCfg()


@configclass
class Ladder6EnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder6RewardsCfg = Ladder6RewardsCfg()


@configclass
class Ladder1StepsEnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder1StepsRewardsCfg = Ladder1StepsRewardsCfg()


@configclass
class Ladder2DragEnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder2DragRewardsCfg = Ladder2DragRewardsCfg()


@configclass
class Ladder2BounceEnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder2BounceRewardsCfg = Ladder2BounceRewardsCfg()


@configclass
class Ladder2FidgetEnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder2FidgetRewardsCfg = Ladder2FidgetRewardsCfg()


@configclass
class Ladder2PairedEnvCfg(ScorbiFlatEnvCfg):
    rewards: Ladder2PairedRewardsCfg = Ladder2PairedRewardsCfg()
