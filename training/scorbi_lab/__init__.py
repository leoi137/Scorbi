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
for _id, _cfg in (("Scorbi-Velocity-Flat-StockReward", "ScorbiFlatStockRewardEnvCfg"), ("Scorbi-Velocity-Flat-LinVel", "ScorbiFlatLinVelEnvCfg")):
    gym.register(
        id=_id,
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"{__name__}.variants:{_cfg}",
            "rsl_rl_cfg_entry_point": f"{__name__}.agent_cfg:ScorbiFlatPPORunnerCfg",
            "default_agent": "rsl_rl",
        },
    )
