"""The action term: the policy drives the 12 leg joints, a script drives the arm.

On the website the arm is moved by script while the policy walks. Here the arm's three position
targets are held in ``arm_target`` (one row per robot, in ARM_JOINTS order) and sent on every
control step. It starts at the standing pose; arm randomisation writes other poses into it.
Without this the arm joints have no target of their own and are driven to zero.
"""

import torch

from isaaclab.envs.mdp.actions.actions_cfg import JointPositionActionCfg
from isaaclab.envs.mdp.actions.joint_actions import JointPositionAction
from isaaclab.utils import configclass

from .robot import ARM_JOINTS


class LegActionWithScriptedArm(JointPositionAction):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        ids, names = self._asset.find_joints(ARM_JOINTS, preserve_order=True)
        assert list(names) == ARM_JOINTS, names
        self._arm_joint_ids = ids
        self.arm_target: torch.Tensor = self._asset.data.default_joint_pos.torch[:, ids].clone()

    def apply_actions(self):
        super().apply_actions()
        self._asset.set_joint_position_target_index(target=self.arm_target, joint_ids=self._arm_joint_ids)


@configclass
class LegActionWithScriptedArmCfg(JointPositionActionCfg):
    class_type: type = LegActionWithScriptedArm
