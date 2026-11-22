"""The command sampler. See commands.py for what it does and why."""

from collections.abc import Sequence

import torch

from isaaclab.envs.mdp.commands.velocity_command import UniformVelocityCommand

from .commands import ScorbiVelocityCommandCfg


class ScorbiVelocityCommand(UniformVelocityCommand):
    """`UniformVelocityCommand` with only the sampling changed. Standing robots are zeroed by the parent afterwards."""

    cfg: ScorbiVelocityCommandCfg

    def __init__(self, cfg: ScorbiVelocityCommandCfg, env) -> None:
        r = cfg.ranges
        if cfg.heading_command:
            raise ValueError("heading mode recomputes the turn rate every step and would bypass the floor")
        if not 0.0 <= cfg.min_speed < min(-r.lin_vel_x[0], r.lin_vel_x[1], -r.lin_vel_y[0], r.lin_vel_y[1]):
            raise ValueError(f"min_speed {cfg.min_speed} is outside the linear ranges {r.lin_vel_x}, {r.lin_vel_y}")
        if not 0.0 <= cfg.min_turn < min(-r.ang_vel_z[0], r.ang_vel_z[1]):
            raise ValueError(f"min_turn {cfg.min_turn} is outside the turn range {r.ang_vel_z}")
        super().__init__(cfg, env)

    def _resample_command(self, env_ids: Sequence[int]) -> None:
        super()._resample_command(env_ids)
        cmd = self.vel_command_b[env_ids]
        n = cmd.shape[0]
        # drive: the planar speed is never between zero and the floor
        speed = torch.linalg.norm(cmd[:, :2], dim=1, keepdim=True)
        forward = torch.tensor([1.0, 0.0], device=self.device).expand(n, 2)
        direction = torch.where(speed > 1e-6, cmd[:, :2] / speed.clamp(min=1e-6), forward)
        linear = direction * speed.clamp(min=self.cfg.min_speed)
        # drive: a small turn rate is a straight walk
        turn = torch.where(cmd[:, 2].abs() < self.cfg.min_turn, torch.zeros_like(cmd[:, 2]), cmd[:, 2])
        # spin: no linear speed, a real turn rate, either way
        spin = torch.rand(n, device=self.device) < self.cfg.rel_spin_envs
        top = torch.where(torch.rand(n, device=self.device) < 0.5, self.cfg.ranges.ang_vel_z[0], self.cfg.ranges.ang_vel_z[1])
        size = self.cfg.min_turn + torch.rand(n, device=self.device) * (top.abs() - self.cfg.min_turn)
        linear = torch.where(spin[:, None], torch.zeros_like(linear), linear)
        turn = torch.where(spin, torch.sign(top) * size, turn)
        self.vel_command_b[env_ids, :2] = linear
        self.vel_command_b[env_ids, 2] = turn
