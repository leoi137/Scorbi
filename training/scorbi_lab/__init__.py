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
_VARIANTS += [("Scorbi-Velocity-Flat-Production-Fidget", "production:ProductionFidgetEnvCfg")]  # for skill 5: the recipe + fidget at rest
_VARIANTS += [("Scorbi-Velocity-Flat-Production-Fast", "production:ProductionFastEnvCfg")]  # the plain production recipe, forward commands up to 0.40 m/s
_VARIANTS += [("Scorbi-Velocity-Flat-Production-Fast-Limit", "production:ProductionFastLimitEnvCfg")]  # the same with a price on leg joint speed over the servo's
_VARIANTS += [("Scorbi-Velocity-Flat-Remote", "production:RemoteEnvCfg")]  # Production-Fast-Limit with every direction faster, for a remote control
# The fast-walk probes: forward commands up to 0.40 m/s (fast.py).
_VARIANTS += [("Scorbi-Velocity-Flat-Fast", "fast:FastEnvCfg"), ("Scorbi-Velocity-Flat-Fast-Narrow", "fast:FastNarrowEnvCfg")]
_VARIANTS += [("Scorbi-Velocity-Flat-TopSpeed", "fast:TopSpeedEnvCfg"), ("Scorbi-Velocity-Flat-AllFast", "fast:AllFastEnvCfg")]  # past 0.8 mph; every direction faster
_VARIANTS += [("Scorbi-Velocity-Flat-Remote-Probe", "fast:RemoteProbeEnvCfg")]  # AllFast with slow commands kept common and a price on leg speed
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
