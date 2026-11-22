"""Isaac Lab tasks for Scorbi. Importing this module registers them."""

import gymnasium as gym

gym.register(
    id="Scorbi-Velocity-Flat",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.env_cfg:ScorbiFlatEnvCfg",
        "rsl_rl_cfg_entry_point": f"{__name__}.agent_cfg:ScorbiFlatPPORunnerCfg",
        "default_agent": "rsl_rl",
    },
)

# Probes: one thing changed each (variants.py).
_VARIANTS = [("Scorbi-Velocity-Flat-StockReward", "variants:ScorbiFlatStockRewardEnvCfg"), ("Scorbi-Velocity-Flat-LinVel", "variants:ScorbiFlatLinVelEnvCfg")]
_VARIANTS += [("Scorbi-Velocity-Flat-Tall", "variants:ScorbiFlatTallEnvCfg")]  # a What If: paid only for being tall
# The reward ladder: rung n has the first n terms of ladder.LADDER on top of tracking (ladder.py).
_VARIANTS += [(f"Scorbi-Velocity-Flat-Ladder{n}", f"ladder:Ladder{n}EnvCfg") for n in range(1, 7)]
_VARIANTS += [("Scorbi-Velocity-Flat-Ladder1-Steps", "ladder:Ladder1StepsEnvCfg")]  # rung 1 + long steps
_VARIANTS += [(f"Scorbi-Velocity-Flat-Ladder2-{n}", f"ladder:Ladder2{n}EnvCfg") for n in ("Drag", "Bounce", "Fidget", "Paired")]  # rung 2 + one of rungs 4 to 6
# The production walk: the chosen recipe with the first n disturbance groups on (production.py).
_VARIANTS += [(f"Scorbi-Velocity-Flat-Walk-G{n}", f"production:WalkG{n}EnvCfg") for n in range(0, 9)]
_VARIANTS += [("Scorbi-Velocity-Flat-Production", "production:ProductionEnvCfg")]  # block E: the chosen recipe, every group that passed
_VARIANTS += [("Scorbi-Velocity-Flat-Production-Plain", "production:ProductionPlainEnvCfg")]  # the comparison: rung 2 alone, every group
for _id, _cfg in _VARIANTS:
    gym.register(
        id=_id,
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"{__name__}.{_cfg}",
            "rsl_rl_cfg_entry_point": f"{__name__}.agent_cfg:ScorbiFlatPPORunnerCfg",
            "default_agent": "rsl_rl",
        },
    )
