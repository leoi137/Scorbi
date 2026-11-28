"""The fast-walk probes: how fast can Scorbi walk? (research 0020)

Every run so far was told to walk at 0.15 m/s forward at most (0.34 mph), because the website asks for
0.12 m/s. These tasks raise the forward command to 0.40 m/s (0.9 mph), so that 0.31 and 0.36 m/s
(0.7 and 0.8 mph) are inside the trained range. Everything else is rung 2 of the reward ladder, the
recipe the website candidate was trained with, with no disturbances.

The width of the tracking reward is the open choice. The plan's rule (half the top command) gives
0.20 m/s, and a reward that wide let the stock-reward run stand still when told to stand (research
0007). The two tasks differ only in that width.
"""

from isaaclab.utils import configclass

from .env_cfg import ScorbiFlatEnvCfg
from .ladder import Ladder2RewardsCfg, Ladder2SpeedRewardsCfg

FAST_FORWARD = (-0.12, 0.40)
"""Forward command range [m/s]. Backward, sideways and turning are unchanged."""


@configclass
class FastEnvCfg(ScorbiFlatEnvCfg):
    """Task ``Scorbi-Velocity-Flat-Fast``: rung 2, forward commands up to 0.40 m/s, tracking width 0.15 m/s."""

    rewards: Ladder2RewardsCfg = Ladder2RewardsCfg()
    lin_std: float = 0.15

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.ranges.lin_vel_x = FAST_FORWARD
        self.rewards.track_twist_exp.params["lin_std"] = self.lin_std


@configclass
class FastNarrowEnvCfg(FastEnvCfg):
    """Task ``Scorbi-Velocity-Flat-Fast-Narrow``: the same with the tracking width every other run has (0.075 m/s)."""

    lin_std: float = 0.075


@configclass
class TopSpeedEnvCfg(FastNarrowEnvCfg):
    """Task ``Scorbi-Velocity-Flat-TopSpeed``: forward commands up to 0.55 m/s (1.2 mph), to find the ceiling (research 0023)."""

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.ranges.lin_vel_x = (-0.12, 0.55)


@configclass
class AllFastEnvCfg(FastNarrowEnvCfg):
    """Task ``Scorbi-Velocity-Flat-AllFast``: every direction faster, for the remote control (research 0023).

    Forward and backward to 0.40 m/s (0.9 mph), sideways to 0.30 m/s (0.67 mph), turning to 2.5 rad/s.
    """

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.ranges.lin_vel_x = (-0.40, 0.40)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.30, 0.30)
        self.commands.base_velocity.ranges.ang_vel_z = (-2.5, 2.5)


@configclass
class RemoteProbeEnvCfg(AllFastEnvCfg):
    """Task ``Scorbi-Velocity-Flat-Remote-Probe``: ``AllFast`` with slow commands kept common and a price on leg speed (research 0026).

    Two changes against ``all_fast_s1``, because the long run needs both and the day has room for one probe:
    40% of the robots draw from ranges 0.3 times as wide, and the reward gains ``leg_speed_over``.
    """

    rewards: Ladder2SpeedRewardsCfg = Ladder2SpeedRewardsCfg()

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.rel_slow_envs = 0.4
