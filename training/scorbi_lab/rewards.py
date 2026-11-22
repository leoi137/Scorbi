"""Scorbi's own reward terms."""

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
