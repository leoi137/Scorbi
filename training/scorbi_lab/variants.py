"""Variants of the flat task for probes: each changes one thing (training plan, block C).

Each is its own task name, so a run's manifest says which one it was and the evaluation rebuilds
the same task from that name.
"""

from isaaclab.envs.mdp.commands.commands_cfg import UniformVelocityCommandCfg
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.utils import configclass
from isaaclab.utils.noise import UniformNoiseCfg as Unoise

import isaaclab_tasks.core.velocity.mdp as mdp

from .env_cfg import TRAIN_RANGES, ObservationsCfg, ScorbiFlatEnvCfg


@configclass
class StockRewardsCfg:
    """Isaac Lab's stock tracking reward: two separate terms, 0.5 wide.

    0.5 m/s is over three times Scorbi's top speed, so a robot that stands still is paid almost in
    full. This is the "standing still" probe: the reward is expected to fail, and that is the point.
    """

    track_lin_vel_xy_exp = RewTerm(func=mdp.track_lin_vel_xy_exp, weight=1.0, params={"command_name": "base_velocity", "std": 0.5})
    track_ang_vel_z_exp = RewTerm(func=mdp.track_ang_vel_z_exp, weight=0.5, params={"command_name": "base_velocity", "std": 0.5})


@configclass
class StockCommandsCfg:
    """Isaac Lab's stock uniform sampler over Scorbi's ranges: most commands are close to zero."""

    base_velocity = UniformVelocityCommandCfg(
        asset_name="robot",
        resampling_time_range=(10.0, 10.0),
        rel_standing_envs=0.02,
        rel_heading_envs=0.0,
        heading_command=False,
        debug_vis=False,
        ranges=UniformVelocityCommandCfg.Ranges(heading=None, **TRAIN_RANGES),
    )


@configclass
class ScorbiFlatStockRewardEnvCfg(ScorbiFlatEnvCfg):
    rewards: StockRewardsCfg = StockRewardsCfg()
    commands: StockCommandsCfg = StockCommandsCfg()


@configclass
class LinVelObservationsCfg(ObservationsCfg):
    @configclass
    class PolicyCfg(ObservationsCfg.PolicyCfg):
        """The 51 numbers plus the body's own linear velocity, which the website knows and the real robot does not: 54."""

        base_lin_vel = ObsTerm(func=mdp.base_lin_vel, noise=Unoise(n_min=-0.1, n_max=0.1))

    policy: PolicyCfg = PolicyCfg()


@configclass
class ScorbiFlatLinVelEnvCfg(ScorbiFlatEnvCfg):
    observations: LinVelObservationsCfg = LinVelObservationsCfg()
