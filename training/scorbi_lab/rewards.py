"""Scorbi's own reward and termination terms."""

import torch

from isaaclab.managers import SceneEntityCfg


def track_twist_exp(env, command_name: str, lin_std: float, ang_std: float, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Paid for following the whole command at once: forward, sideways and turn.

    exp(-(linear error / lin_std)^2 - (turn error / ang_std)^2), the product of Isaac Lab's two
    tracking kernels. With the two kernels as separate terms, a robot standing still is paid in
    full for every axis that happens to be commanded zero: the turn term on a straight walk, the
    linear term on a spin. As one term, standing still only pays when the robot is told to stand.
    """
    asset = env.scene[asset_cfg.name]
    command = env.command_manager.get_command(command_name)
    lin = torch.sum(torch.square(command[:, :2] - asset.data.root_lin_vel_b.torch[:, :2]), dim=1)
    ang = torch.square(command[:, 2] - asset.data.root_ang_vel_b.torch[:, 2])
    return torch.exp(-lin / lin_std**2 - ang / ang_std**2)


def blow_up(env, max_height: float = 1.0, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """True for a robot the simulator has lost: a state that is not a number, or a body a metre above the floor."""
    data = env.scene[asset_cfg.name].data
    pos = data.root_link_pos_w.torch
    height = pos[:, 2] - env.scene.env_origins[:, 2]
    return ~torch.isfinite(pos).all(dim=1) | ~torch.isfinite(data.joint_pos.torch).all(dim=1) | (height > max_height)


def tall(env, stand_height: float = 0.0717, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Paid for how high the body is above the floor, in standing heights: 1.0 when it stands. Nothing else is paid."""
    height = env.scene[asset_cfg.name].data.root_link_pos_w.torch[:, 2] - env.scene.env_origins[:, 2]
    return torch.nan_to_num(height / stand_height, nan=0.0, posinf=0.0, neginf=0.0).clamp(min=0.0)
