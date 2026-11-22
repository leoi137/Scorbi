"""The action term: the policy drives the 12 leg joints, a script drives the arm.

On the website the arm is moved by script while the policy walks. Here the arm's three position
targets are held in ``arm_target`` (one row per robot, in ARM_JOINTS order) and sent on every
control step. Without this the arm joints have no target of their own and are driven to zero.

The term also holds the disturbances that sit between the policy and the servos (training plan,
part 5.5). All are off unless the task's config turns them on, and the evaluation turns them off:

  arm        each episode starts in one of the website's arm poses and sometimes moves to another
  hand-off   at random moments a script takes the legs to a pose, holds it, and gives them back
  delay      the leg targets reach the servos 0 to N control steps late
  zero       each servo's zero is off by a small fixed angle
"""

import torch

from isaaclab.envs.mdp.actions.actions_cfg import JointPositionActionCfg
from isaaclab.envs.mdp.actions.joint_actions import JointPositionAction
from isaaclab.utils import configclass

from .robot import ARM_JOINTS

HANDOFF_BLEND = 0.3  # s a script takes to move the legs from where they are to its pose


class LegActionWithScriptedArm(JointPositionAction):
    cfg: "LegActionWithScriptedArmCfg"

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        ids, names = self._asset.find_joints(ARM_JOINTS, preserve_order=True)
        assert list(names) == ARM_JOINTS, names
        self._arm_joint_ids = ids
        n, device = self.num_envs, self.device
        self._arm_rest = self._asset.data.default_joint_pos.torch[:, ids].clone()
        self.arm_target: torch.Tensor = self._arm_rest.clone()
        limits = self._asset.data.joint_pos_limits.torch[:, self._joint_ids]
        self._lowest, self._highest = limits[..., 0].clone(), limits[..., 1].clone()
        self._stance = self._asset.data.default_joint_pos.torch[:, self._joint_ids].clone()

        # arm poses
        self._arm_goal = self._arm_rest.clone()
        self._arm_poses = None
        if cfg.arm_poses:
            arm_limits = self._asset.data.joint_pos_limits.torch[0, ids]
            poses = torch.tensor(list(cfg.arm_poses.values()), dtype=torch.float32, device=device)
            self._arm_poses = torch.clamp(poses, arm_limits[:, 0], arm_limits[:, 1])
        # delay: the last few leg targets, newest first
        self._delay = torch.zeros(n, dtype=torch.long, device=device)
        self._sent = self._stance[:, None, :].repeat(1, cfg.delay_steps + 1, 1)
        # zero offset
        self._zero = torch.zeros(n, self.action_dim, device=device)
        # hand-off: control steps left, steps done, where the legs were and where the script takes them
        self._script_left = torch.zeros(n, dtype=torch.long, device=device)
        self._script_done = torch.zeros(n, dtype=torch.long, device=device)
        self._script_from = self._stance.clone()
        self._script_pose = self._stance.clone()
        self._rows = torch.arange(n, device=device)

    @property
    def scripted(self) -> torch.Tensor:
        """True for robots whose legs a script holds on this control step."""
        return self._script_left > 0

    def process_actions(self, actions: torch.Tensor):
        super().process_actions(actions)
        cfg, dt = self.cfg, self._env.step_dt
        targets = self._processed_actions
        if cfg.handoff_every_s > 0:
            targets = self._hand_off(targets, dt)
        if cfg.delay_steps > 0:
            self._sent = torch.roll(self._sent, 1, dims=1)
            self._sent[:, 0] = targets
            targets = self._sent[self._rows, self._delay]
        # A servo cannot be told to go past its range, and the website clamps its targets the same way.
        self._processed_actions = torch.clamp(targets + self._zero, self._lowest, self._highest)
        if self._arm_poses is not None:
            change = torch.rand(self.num_envs, device=self.device) < dt / cfg.arm_change_every_s
            pick = torch.randint(len(self._arm_poses), (self.num_envs,), device=self.device)
            self._arm_goal = torch.where(change[:, None], self._arm_poses[pick], self._arm_goal)
            step = cfg.arm_speed * dt
            self.arm_target += torch.clamp(self._arm_goal - self.arm_target, -step, step)

    def _hand_off(self, targets: torch.Tensor, dt: float) -> torch.Tensor:
        cfg, n, device = self.cfg, self.num_envs, self.device
        measured = self._asset.data.joint_pos.torch[:, self._joint_ids]
        start = (self._script_left <= 0) & (torch.rand(n, device=device) < dt / cfg.handoff_every_s)
        low, high = cfg.handoff_seconds
        seconds = low + (high - low) * torch.rand(n, device=device)
        self._script_left = torch.where(start, torch.round(seconds / dt).long(), self._script_left)
        self._script_done = torch.where(start, torch.zeros_like(self._script_done), self._script_done)
        scatter = (2 * torch.rand(n, self.action_dim, device=device) - 1) * cfg.handoff_scatter
        self._script_pose = torch.where(start[:, None], self._stance + scatter, self._script_pose)
        self._script_from = torch.where(start[:, None], measured, self._script_from)
        busy = self._script_left > 0
        if not busy.any():
            return targets
        blend = torch.clamp((self._script_done + 1) * dt / HANDOFF_BLEND, max=1.0)[:, None]
        scripted = self._script_from + (self._script_pose - self._script_from) * blend
        targets = torch.where(busy[:, None], scripted, targets)
        # The policy is not asked while a script holds the legs. It is told to stand, and its "last
        # action" is set from the measured joint angles, as the website does when it hands back.
        last = (measured - self._stance) / self._scale
        manager = self._env.action_manager
        manager._action[:] = torch.where(busy[:, None], last, manager._action)
        self._raw_actions[:] = torch.where(busy[:, None], last, self._raw_actions)
        command = self._env.command_manager.get_term(cfg.command_name)
        command.vel_command_b[busy] = 0.0
        self._script_left = torch.where(busy, self._script_left - 1, self._script_left)
        self._script_done = torch.where(busy, self._script_done + 1, self._script_done)
        # still held: no new command in the meantime. Handed back: a new command on the next step.
        command.time_left[busy] = 1.0
        command.time_left[busy & (self._script_left <= 0)] = 0.0
        return targets

    def apply_actions(self):
        super().apply_actions()
        self._asset.set_joint_position_target_index(target=self.arm_target, joint_ids=self._arm_joint_ids)

    def reset(self, env_ids=None) -> None:
        super().reset(env_ids)
        cfg, device = self.cfg, self.device
        ids = self._rows if env_ids is None else self._rows[env_ids]
        k = len(ids)
        self._script_left[ids] = 0
        self._sent[ids] = self._stance[ids, None, :]
        if cfg.delay_steps > 0:
            self._delay[ids] = torch.randint(cfg.delay_steps + 1, (k,), device=device)
        if cfg.zero_offset > 0:
            self._zero[ids] = (2 * torch.rand(k, self.action_dim, device=device) - 1) * cfg.zero_offset
        if self._arm_poses is not None:
            pose = self._arm_poses[torch.randint(len(self._arm_poses), (k,), device=device)]
            self._arm_goal[ids] = pose
            self.arm_target[ids] = pose


@configclass
class LegActionWithScriptedArmCfg(JointPositionActionCfg):
    class_type: type = LegActionWithScriptedArm

    arm_poses: dict[str, tuple[float, float, float]] | None = None
    """Arm poses to start in and move between: name -> (arm_shoulder, arm_elbow, claw) in rad. None holds the standing pose."""
    arm_change_every_s: float = 8.0
    """With arm poses: the arm is sent to another pose about this often [s]."""
    arm_speed: float = 2.0
    """How fast the arm's targets move to a new pose [rad/s]."""

    handoff_every_s: float = 0.0
    """A script takes the legs about this often [s]. 0 is never."""
    handoff_seconds: tuple[float, float] = (0.5, 2.0)
    """How long the script holds the legs [s]."""
    handoff_scatter: float = 0.15
    """The script's pose is the stance with each leg joint off by up to this much [rad]."""
    command_name: str = "base_velocity"

    delay_steps: int = 0
    """Each robot's leg targets arrive 0 to this many control steps late (fixed per episode)."""
    zero_offset: float = 0.0
    """Each leg servo's zero is off by up to this much [rad] (fixed per episode)."""
