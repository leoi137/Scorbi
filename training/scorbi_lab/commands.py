"""The command sampler's config: drive means drive, and standing and spinning are asked for on purpose.

A plain uniform sampler puts many commands near zero, where standing still is nearly the right
answer, and a robot can then be paid for parking. Ported from Bestiary's dead-zone sampler
(leoi137/Bestiary, `bestiary/isaac/commands.py`), changed for a robot that must also walk
sideways and turn on the spot:

  stand  `rel_standing_envs` of robots: the whole command is zero (the parent's own mechanism).
  spin   `rel_spin_envs` of the rest: no linear speed, and a turn rate of at least `min_turn`.
  drive  the others: the planar speed is raised to `min_speed` when it is below it, keeping its
         direction, and a turn rate under `min_turn` becomes exactly zero (a straight walk).

Nothing that runs the simulator is imported here: Isaac Lab imports config modules before the
simulation exists. The sampler itself is in commands_impl.py, named by the lazy string below.
"""

from isaaclab.envs.mdp.commands.commands_cfg import UniformVelocityCommandCfg
from isaaclab.utils import configclass


@configclass
class ScorbiVelocityCommandCfg(UniformVelocityCommandCfg):
    class_type: type | str = "{DIR}.commands_impl:ScorbiVelocityCommand"

    min_speed: float = 0.06
    """Smallest planar speed a driving robot is told to walk at [m/s]."""

    min_turn: float = 0.3
    """Turn rates under this become exactly zero; a spinning robot turns at least this fast [rad/s]."""

    rel_spin_envs: float = 0.15
    """Share of the robots that are not standing which are told to turn on the spot."""
