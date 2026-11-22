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
# The reward ladder: rung n has the first n terms of ladder.LADDER on top of tracking (ladder.py).
_VARIANTS += [(f"Scorbi-Velocity-Flat-Ladder{n}", f"ladder:Ladder{n}EnvCfg") for n in range(1, 7)]
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
