"""The production walk: the chosen reward recipe, with disturbances added one group at a time (training plan, 5.5).

Task ``Scorbi-Velocity-Flat-Walk-G<n>`` has the first n groups of GROUPS switched on, so G0 is the
recipe alone and G8 is everything. Each group is a probe of its own before the long run.

The numbers are scaled to a 1.25 kg robot that walks at 0.1 m/s. Where they differ from the plan's
proposals, the reason is in research entry 0007.
"""

import math

import torch

from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass

import isaaclab_tasks.core.velocity.mdp as mdp

from .env_cfg import EventsCfg, ScorbiFlatEnvCfg
from .ladder import Ladder1RewardsCfg, Ladder2BounceRewardsCfg, Ladder2RewardsCfg

# The group probes (Walk-G1 to G8) were queued while block D was undecided and keep rung 1's reward,
# so that they stay comparable with each other. The production run has the chosen recipe (below).
RecipeRewardsCfg = Ladder1RewardsCfg

# The order the groups are added in: the plan's.
GROUPS = ["arm", "hand_off", "shoves", "friction", "mass", "motors", "delay", "resets"]

# The website's arm poses (src/sim/controller.ts: REST, HIGH, the bow's start, CARRY), as
# (arm_shoulder, arm_elbow, claw) joint angles: elbow = hand angle - upper arm angle.
ARM_POSES = {
    "rest": (1.25, -1.80, -0.384),
    "wave": (1.45, -1.35, 0.0),
    "grab": (0.0, -1.0, 0.45),
    "carry": (1.6, -1.8, -0.05),
}


def shove(env, env_ids: torch.Tensor, speed: tuple[float, float], asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")):
    """A step change in the base's speed along the floor: any direction, `speed` m/s. The evaluation shoves the same way."""
    asset = env.scene[asset_cfg.name]
    vel = asset.data.root_vel_w.torch[env_ids].clone()
    n = vel.shape[0]
    angle = 2 * math.pi * torch.rand(n, device=vel.device)
    size = speed[0] + (speed[1] - speed[0]) * torch.rand(n, device=vel.device)
    vel[:, 0] += size * torch.cos(angle)
    vel[:, 1] += size * torch.sin(angle)
    asset.write_root_velocity_to_sim_index(root_velocity=vel, env_ids=env_ids)


def scale_motor_strength(env, env_ids: torch.Tensor | None, scale: tuple[float, float], asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")):
    """Each servo's torque limit times a number in `scale`, drawn once per servo."""
    asset = env.scene[asset_cfg.name]
    limits = asset.data.joint_effort_limits.torch.clone()
    if env_ids is None:
        env_ids = torch.arange(env.num_envs, device=limits.device)
    factor = scale[0] + (scale[1] - scale[0]) * torch.rand(len(env_ids), limits.shape[1], device=limits.device)
    asset.write_joint_effort_limit_to_sim_index(limits=limits[env_ids] * factor, env_ids=env_ids)


@configclass
class WalkEventsCfg(EventsCfg):
    """Every group's events. A task switches off the groups it does not have (WalkEnvCfg)."""

    # arm: an 8 g block in the claw. Every robot carries 0 to 8 g, not "some robots carry 8 g".
    block_in_claw = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={"asset_cfg": SceneEntityCfg("robot", body_names="finger"), "mass_distribution_params": (0.0, 0.008), "operation": "add", "distribution": "uniform", "min_mass": 1e-6},
    )
    # shoves: every 4 to 8 s. Scorbi shrugs off anything under 0.5 m/s and half fall at 1.5 (research 0006).
    shove = EventTerm(func=shove, mode="interval", interval_range_s=(4.0, 8.0), params={"speed": (0.2, 1.0)})
    # friction: each foot's own, around the website's 1.1. This backend has one coefficient per shape.
    foot_friction = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*_foot"),
            "static_friction_range": (0.5, 1.3),
            "dynamic_friction_range": (0.5, 1.3),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 64,
        },
    )
    # mass: grams added to the body, from 50 g lighter to 150 g heavier. The centre of mass is not
    # shifted: Isaac Lab warns that doing so on this backend can make the simulation unstable.
    added_mass = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={"asset_cfg": SceneEntityCfg("robot", body_names="base"), "mass_distribution_params": (-0.05, 0.15), "operation": "add", "distribution": "uniform", "min_mass": 1e-6},
    )
    # motors: gains and strength of every servo; the zero offset is in the action term.
    motor_gains = EventTerm(
        func=mdp.randomize_actuator_gains,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
            "stiffness_distribution_params": (0.75, 1.25),
            "damping_distribution_params": (0.75, 1.25),
            "operation": "scale",
            "distribution": "uniform",
        },
    )
    motor_strength = EventTerm(func=scale_motor_strength, mode="startup", params={"scale": (0.8, 1.2)})


# The events each group owns. The other groups change the action term or the resets (WalkEnvCfg).
GROUP_EVENTS = {"arm": ["block_in_claw"], "shoves": ["shove"], "friction": ["foot_friction"], "mass": ["added_mass"], "motors": ["motor_gains", "motor_strength"]}


@configclass
class WalkEnvCfg(ScorbiFlatEnvCfg):
    rewards: RecipeRewardsCfg = RecipeRewardsCfg()
    events: WalkEventsCfg = WalkEventsCfg()
    disturbances: int = 0
    """How many of GROUPS are on, in order."""

    def __post_init__(self):
        super().__post_init__()
        on = GROUPS[: self.disturbances]
        for group, names in GROUP_EVENTS.items():
            if group not in on:
                for name in names:
                    setattr(self.events, name, None)
        action = self.actions.joint_pos
        if "arm" in on:
            action.arm_poses = dict(ARM_POSES)
        if "hand_off" in on:
            action.handoff_every_s = 15.0  # about once per 20 s episode, for 0.5 to 2 s
        if "motors" in on:
            action.zero_offset = 0.02
        if "delay" in on:
            action.delay_steps = 2  # 0, 1 or 2 control steps; zero is included because the website has none
        if "resets" in on:
            self.events.reset_robot_joints.params["position_range"] = (-0.1, 0.1)
            self.events.reset_base.params["velocity_range"] = {
                "x": (-0.05, 0.05), "y": (-0.05, 0.05), "roll": (-0.3, 0.3), "pitch": (-0.3, 0.3), "yaw": (-0.3, 0.3),
            }


@configclass
class WalkG0EnvCfg(WalkEnvCfg):
    disturbances: int = 0


@configclass
class WalkG1EnvCfg(WalkEnvCfg):
    disturbances: int = 1


@configclass
class WalkG2EnvCfg(WalkEnvCfg):
    disturbances: int = 2


@configclass
class WalkG3EnvCfg(WalkEnvCfg):
    disturbances: int = 3


@configclass
class WalkG4EnvCfg(WalkEnvCfg):
    disturbances: int = 4


@configclass
class WalkG5EnvCfg(WalkEnvCfg):
    disturbances: int = 5


@configclass
class WalkG6EnvCfg(WalkEnvCfg):
    disturbances: int = 6


@configclass
class WalkG7EnvCfg(WalkEnvCfg):
    disturbances: int = 7


@configclass
class WalkG8EnvCfg(WalkEnvCfg):
    disturbances: int = 8


# ── the production run (block E) ──────────────────────────────────────────
# The recipe chosen in block D (research 0011): rung 2 plus the body-bounce term.
# Tracking, action change, a price on falling, leg torque, vertical body speed with roll and pitch rate.
ProductionRewardsCfg = Ladder2BounceRewardsCfg


@configclass
class ProductionEnvCfg(WalkEnvCfg):
    """Task ``Scorbi-Velocity-Flat-Production``: the chosen recipe with the disturbance groups that passed their probes."""

    rewards: ProductionRewardsCfg = ProductionRewardsCfg()
    disturbances: int = 8


@configclass
class ProductionPlainEnvCfg(WalkEnvCfg):
    """Task ``Scorbi-Velocity-Flat-Production-Plain``: the same without the body-bounce term (rung 2 alone).

    On the website's bumpy floor the bounce term stalled on four commands against two (research 0012): it steps
    lower. This is the comparison run.
    """

    rewards: Ladder2RewardsCfg = Ladder2RewardsCfg()
    disturbances: int = 8
